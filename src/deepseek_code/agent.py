from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
from rich.console import Console

from .logging_utils import ConversationLogger
from .tokens import count_message_tokens
from .tools import tool_schemas


@dataclass
class AgentSettings:
    api_key: str
    model: str
    base_url: str = "https://api.deepseek.com"
    max_messages: int = 50
    stream_word_delay_ms: int = 40
    max_context_tokens: int = 32000
    indent_assistant: bool = True
    assistant_indent: str = "  "
    debug: bool = False
    logger: ConversationLogger | None = None
    system_prompt: str | None = None
    append_system_prompt: str | None = None


class DeepSeekAgent:
    def __init__(self, settings: AgentSettings, console: Console, cwd: str | None = None) -> None:
        self.settings = settings
        self.console = console
        self._at_line_start = True
        self.cwd = cwd or os.getcwd()

        prompt = self.settings.system_prompt or self._get_default_prompt()
        if self.settings.append_system_prompt:
            prompt += f"\n\n{self.settings.append_system_prompt}"

        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": prompt,
            }
        ]

    def _get_default_prompt(self) -> str:
        return (
            "You are an expert Python software engineer. You are helpful, direct, and efficient.\n"
            f"CURRENT WORKING DIRECTORY: {self.cwd}\n\n"
            "### OBJECTIVE\n"
            "Your goal is to fulfill the user's request by using tools. If the request asks to find and read specific files, prioritize that action.\n\n"
            "### RULES\n"
            "1. **USE TOOLS**: You have file system tools. Use them to explore and edit code.\n"
            "2. **STAY PUT & PROCEED**: If your current directory matches the user's requested path, you are ALREADY there. Do NOT run 'cd' again. Move immediately to the next sub-task (e.g., list files or read them).\n"
            "3. **PAY ATTENTION**: When a tool returns output (like a file list), READ IT. Do not repeat the same command unnecessarily.\n"
            "4. **FOUND IT? READ IT**: If you find the files requested (`agent.py`, `cli.py`), READ THEM immediately. Do not list directories again unless the user specifically asks.\n"
            "5. **NOLOOPS**: Do not repeat commands. If a command worked, move on.\n"
            "6. **TRUST OUTPUT**: If a tool returns valid output, use it. Do not run the same tool again to 'verify' unless changed.\n"
        )

    def update_system_prompt(self) -> None:
        """Refresh the system prompt with the current CWD."""
        prompt = self.settings.system_prompt or self._get_default_prompt()
        if self.settings.append_system_prompt:
            prompt += f"\n\n{self.settings.append_system_prompt}"

        # Update the first message (system prompt)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = prompt
        else:
            # Fallback if messages are empty or corrupted
            self.messages.insert(0, {"role": "system", "content": prompt})

    def reset(self) -> None:
        self.messages = [self.messages[0]]

    def trim_messages(self) -> None:
        try:
            count = count_message_tokens(self.messages, self.settings.model)
            if self.settings.debug:
                self.console.print(f"[dim]Token usage: {count}/{self.settings.max_context_tokens}[/]")
        except Exception as e:
            if self.settings.debug:
                self.console.print(f"[dim red]Token count error: {e}[/]")

        # FINAL SANITIZATION ONLY
        self._ensure_valid_conversation()

    def _ensure_valid_conversation(self) -> None:
        """Brutally validate and fix conversation structure."""
        if not self.messages:
            return

        valid_messages = [self.messages[0]]  # Always keep system

        for i in range(1, len(self.messages)):
            msg = self.messages[i]
            role = msg.get("role")

            if role == "tool":
                # Tool message MUST follow an Assistant message with tool_calls
                prev = valid_messages[-1]
                if prev.get("role") == "assistant" and prev.get("tool_calls"):
                    valid_messages.append(msg)
                else:
                    if self.settings.debug:
                        self.console.print(f"[dim yellow]Dropping orphan tool message (index {i})[/]")
                    continue
            else:
                # If the previous message was Assistant with tool_calls, but this message is NOT a tool,
                # then the Assistant message is "hanging" (unanswered). We must remove the Assistant message too.
                # However, this modifies 'valid_messages' in place.
                prev = valid_messages[-1]
                if prev.get("role") == "assistant" and prev.get("tool_calls"):
                    # Found an assistant call not followed by a tool.
                    # We drop the PREVIOUS assistant message.
                    if self.settings.debug:
                        self.console.print("[dim yellow]Dropping hanging assistant call[/]")
                    valid_messages.pop()

                valid_messages.append(msg)

        # Final check: If the last message is Assistant with tool_calls, it's hanging.
        if valid_messages:
            last = valid_messages[-1]
            if last.get("role") == "assistant" and last.get("tool_calls"):
                if self.settings.debug:
                    self.console.print("[dim yellow]Dropping trailing hanging assistant call[/]")
                valid_messages.pop()

        self.messages = valid_messages

    def _log(self, payload: Any) -> None:
        if self.settings.logger:
            self.settings.logger.write(payload)

    def _request_payload(self, use_tools: bool, allowed_tools: set[str] | None) -> dict[str, Any]:
        payload = {
            "model": self.settings.model,
            "messages": self.messages,
            "stream": True,
        }
        if use_tools:
            payload["tools"] = tool_schemas(allowed_tools)
            payload["tool_choice"] = "auto"
        return payload

    def call_model(
        self,
        use_tools: bool = True,
        on_stream_start: callable | None = None,
        allowed_tools: set[str] | None = None,
        stop_event: threading.Event | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        # Debug context size for the user
        self.console.print(f"[dim]Context: {len(self.messages)} messages[/]")

        payload = self._request_payload(use_tools, allowed_tools)
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.base_url}/v1/chat/completions"

        if self.settings.debug:
            self.console.print("[bold cyan]debug[/] request ->", url)
            self.console.print(json.dumps(payload, ensure_ascii=True, indent=2))

        with httpx.Client(timeout=60) as client:
            try:
                return self._streaming_call(client, url, headers, payload, on_stream_start, stop_event)
            except Exception as exc:
                self.console.print(f"[red]Streaming failed[/]: {exc}")
                return self._non_streaming_call(client, url, headers, payload)

    def _streaming_call(
        self,
        client: httpx.Client,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        on_stream_start: callable | None,
        stop_event: threading.Event | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        content_chunks: list[str] = []
        buffer = ""
        tool_calls: dict[int, dict[str, Any]] = {}
        started = False
        self._at_line_start = True

        with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if stop_event and stop_event.is_set():
                    break
                if not line:
                    continue

                if line.startswith("data: "):
                    data = line[len("data: ") :]
                else:
                    data = line
                if data.strip() == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue

                delta = payload["choices"][0].get("delta", {})

                # Handle regular content
                if "content" in delta and delta["content"]:
                    if not started and on_stream_start:
                        on_stream_start()
                        started = True
                    text = delta["content"]
                    content_chunks.append(text)
                    if self.settings.stream_word_delay_ms <= 0:
                        self.console.print(text, end="", style="white")
                    else:
                        buffer = self._emit_streamed_text(buffer, text)

                # Handle tool calls
                if "tool_calls" in delta:
                    if not started and on_stream_start:
                        on_stream_start()
                        started = True
                    for call in delta["tool_calls"]:
                        index = call.get("index", 0)
                        entry = tool_calls.setdefault(
                            index,
                            {
                                "id": None,
                                "type": "function",
                                "function": {"name": None, "arguments": ""}
                            }
                        )
                        if call.get("id"):
                            entry["id"] = call["id"]
                        func = call.get("function", {})
                        if func.get("name"):
                            entry["function"]["name"] = func["name"]
                        if func.get("arguments"):
                            entry["function"]["arguments"] += func["arguments"]

                # Debug usage info
                if payload.get("usage") and self.settings.debug:
                    self.console.print("\n[bold cyan]debug[/] usage:", payload["usage"])

        if buffer and self.settings.stream_word_delay_ms > 0:
            self._emit_remaining_text(buffer)
        if content_chunks:
            self.console.print("")

        tool_call_list = [tool_calls[idx] for idx in sorted(tool_calls.keys())]
        return "".join(content_chunks), tool_call_list

    def _non_streaming_call(
        self,
        client: httpx.Client,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        payload = dict(payload)
        payload["stream"] = False
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if self.settings.debug:
            self.console.print("[bold cyan]debug[/] response:")
            self.console.print(json.dumps(data, ensure_ascii=True, indent=2))
        message = data["choices"][0]["message"]
        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", [])
        if content:
            self._print_assistant_text(content)
        return content, tool_calls

    def append(self, role: str, content: str, **extra: Any) -> None:
        msg = {"role": role, "content": content}
        msg.update(extra)
        self.messages.append(msg)
        self.trim_messages()
        self._log(msg)

    def append_tool(self, tool_call_id: str, content: str) -> None:
        # Truncate if excessively long to prevent context explosion
        # Limit to 2000 characters (approx 500 tokens)
        MAX_TOOL_OUTPUT = 2000
        if len(content) > MAX_TOOL_OUTPUT:
            preview = content[:1000]
            suffix = content[-500:]
            content = (
                f"{preview}\n"
                f"... [TRUNCATED {len(content) - 1500} chars] ...\n"
                f"{suffix}\n"
                f"\n[SYSTEM: Output truncated to save context. Use 'grep' or 'read_json_chunk' to see specific parts.]"
            )

        msg = {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        self.messages.append(msg)
        self.trim_messages()
        self._log(msg)

    def append_assistant_with_tools(self, content: str, tool_calls: list[dict[str, Any]]) -> None:
        msg = {"role": "assistant", "content": content, "tool_calls": tool_calls}

        # For deepseek-reasoner model, we must include reasoning_content
        # even if empty, when there are tool calls
        if "reasoner" in self.settings.model.lower() and tool_calls:
            msg["reasoning_content"] = ""

        self.messages.append(msg)
        self.trim_messages()
        self._log(msg)

    def backoff_sleep(self, attempt: int) -> None:
        delay = min(2 ** attempt, 8)
        time.sleep(delay)

    def _emit_streamed_text(self, buffer: str, text: str) -> str:
        buffer += text
        last_space = max(buffer.rfind(" "), buffer.rfind("\n"), buffer.rfind("\t"))
        if last_space == -1:
            return buffer
        segment = buffer[: last_space + 1]
        remainder = buffer[last_space + 1 :]
        self._emit_segment(segment)
        return remainder

    def _emit_segment(self, segment: str) -> None:
        delay = max(self.settings.stream_word_delay_ms, 0) / 1000.0
        leading = re.match(r"\s+", segment)
        if leading:
            self.console.print(leading.group(0), end="")
            segment = segment[len(leading.group(0)) :]
        tokens = re.findall(r"\S+\s*", segment)
        for token in tokens:
            if self.settings.indent_assistant and self._at_line_start and token.strip():
                self.console.print(self.settings.assistant_indent, end="")
            self.console.print(token, end="", style="white")
            if token.endswith("\n"):
                self._at_line_start = True
            elif token.strip():
                self._at_line_start = False
            if delay:
                time.sleep(delay)

    def _emit_remaining_text(self, buffer: str) -> None:
        if not buffer:
            return
        if self.settings.indent_assistant and self._at_line_start and buffer.strip():
            self.console.print(self.settings.assistant_indent, end="")
        self.console.print(buffer, end="", style="white")
        if buffer.endswith("\n"):
            self._at_line_start = True
        elif buffer.strip():
            self._at_line_start = False

    def _print_assistant_text(self, content: str) -> None:
        for line in content.splitlines(keepends=True):
            if self.settings.indent_assistant and line.strip():
                self.console.print(self.settings.assistant_indent, end="")
            self.console.print(line, end="", style="white")
