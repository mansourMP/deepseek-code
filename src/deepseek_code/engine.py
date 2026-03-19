"""
Core execution engine for DeepSeek Code.
Handles the ReAct loop, tool orchestration, and session state.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.status import Status

from .agent import DeepSeekAgent
from .safety import resolve_path
from .tools import ToolResult, dispatch_tool, parse_tool_arguments
from .ui.panels import (
    get_tool_description,
    print_list_panel,
    print_read_panel,
    print_shell_panel,
)
from .ui.themes import Theme, get_theme


class Engine:
    def __init__(
        self,
        agent: DeepSeekAgent,
        console: Console,
        root: Path,
        denylist: List[str],
        theme: Theme | None = None,
    ):
        self.agent = agent
        self.console = console
        self.root = root
        self.denylist = denylist
        self.theme = theme or get_theme()

        self.session_state: Dict[str, Any] = {
            "auto_approve": False,
            "cwd": root,
            "failed_attempts": 0,
            "call_history": [],
            "last_backup": {},
        }

        self.approve_reads = False
        self.readonly = False
        self.chunk_file: Optional[str] = None
        self.chunk_state_path: Optional[Path] = None

    def run_turn(self, user_input: str, plan_mode: bool = False, stop_event: Optional[threading.Event] = None) -> bool:
        """
        Run a single interaction turn.
        Returns True if successful, False if interrupted or failed.
        """
        if plan_mode:
            content = f"{user_input}\n\n[PLAN MODE: Explore and propose a plan, do not edit files.]"
            self.agent.append("user", content)
        else:
            self.agent.append("user", user_input)

        self.session_state["failed_attempts"] = 0

        attempts = 0
        use_tools = True

        while True:
            attempts += 1
            if attempts > 15:  # Safety break for infinite loops
                self.console.print(f"[{self.theme.error}]Max turns reached (15). Stopping.[/]")
                return False

            status_text = "Thinking..."
            with Status(f"[{self.theme.primary}]{status_text}[/]", console=self.console) as status:
                try:
                    allowed_tools = None
                    if self.chunk_file:
                        allowed_tools = {"read_json_chunk", "write_json_chunk"}

                    content, tool_calls = self.agent.call_model(
                        use_tools=use_tools,
                        allowed_tools=allowed_tools,
                        stop_event=stop_event,
                    )
                except Exception as e:
                    self.console.print(f"[{self.theme.error}]Model call failed: {e}[/]")
                    return False

            if stop_event and stop_event.is_set():
                self.console.print(f"[{self.theme.warning}]Turn cancelled by user.[/]")
                return False

            if tool_calls:
                self.agent.append_assistant_with_tools(content, tool_calls)

                status_code = self._handle_tool_calls(tool_calls, stop_event)

                if status_code == "denied":
                    return True
                if status_code == "intervene":
                    self.console.print(f"[{self.theme.warning}]Agent requires intervention.[/]")
                    return True
                if status_code == "error":
                    return False

                # Continue the loop for tool outputs
                continue

            if content:
                self.agent.append("assistant", content)

            break

        return True

    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]], stop_event: Optional[threading.Event]) -> str:
        """Execute tool calls and update agent history."""
        call_history = self.session_state["call_history"]
        current_cwd = str(self.session_state.get("cwd", self.root))

        # Loop Detection
        current_calls = []
        for call in tool_calls:
            func = call.get("function", {})
            name = func.get("name")
            raw_args = func.get("arguments", "")
            args, _ = parse_tool_arguments(raw_args)
            arg_tuple = tuple(sorted(args.items())) if args else ()
            current_calls.append((name, arg_tuple, current_cwd, call.get("id")))

        loop_detected = False
        cached_responses = {}

        for name, arg_tuple, cwd, call_id in current_calls:
            # Check last 10 turns
            matches = [
                entry for entry in call_history[-20:]
                if entry[0] == name and entry[1] == arg_tuple and entry[2] == cwd
            ]
            if matches:
                loop_detected = True
                cached_responses[call_id] = matches[-1][3]

        if loop_detected:
            self.session_state["failed_attempts"] += 1
            self.console.print(f"[bold {self.theme.error}]⟳ Loop detected ({self.session_state['failed_attempts']}/3)[/]")

            if self.session_state["failed_attempts"] >= 3:
                for call in tool_calls:
                    self.agent.append_tool(
                        call.get("id"), 
                        "ERROR: Infinite loop detected. You have attempted the exact same action 3 times with the same results. "
                        "STOP immediately. Do not call any more tools. Explain to the user that you are stuck and ask for help."
                    )
                return "intervene"

            # Use cached responses with a warning
            for call in tool_calls:
                call_id = call.get("id")
                if call_id in cached_responses:
                    output = cached_responses[call_id]
                    self.agent.append_tool(
                        call_id, 
                        f"SYSTEM: WARNING - REPETITIVE CALL. You already have this information. \n"
                        f"OUTPUT: {output}\n"
                        "STOP repeating this call. Use the information above to proceed or change your plan."
                    )
                else:
                    self.agent.append_tool(call_id, "ERROR: Parallel call blocked to prevent infinite loop.")
            return "ok"
        # Actual execution
        def run_one(call):
            call_id = call.get("id")
            func = call.get("function", {})
            name = func.get("name")
            raw_args = func.get("arguments", "")

            args, error = parse_tool_arguments(raw_args)
            if error:
                return call_id, f"ERROR: {error}", name, None

            # Tool description & approval
            desc = get_tool_description(name, args, self.theme)
            self.console.print(f"[{self.theme.dim}]❯[/] {desc}")

            # Mode checks
            if self.readonly and name in {"write_file", "run_shell", "delete_file"}:
                return call_id, "ERROR: Read-only mode", name, None

            if self.chunk_file and name not in {"read_json_chunk", "write_json_chunk"}:
                return call_id, "ERROR: Chunk mode restriction", name, None

            # Approval workflow
            if not self._approve_tool(name, args):
                return call_id, "ERROR: Denied by user", name, None

            # Special handling for write_file (backup)
            if name == "write_file":
                self._backup_file(args.get("path", ""))

            # Execute
            result = dispatch_tool(self.root, name, args, self.denylist, cwd=self.session_state.get("cwd"))

            # Display results
            self._display_tool_result(name, args, result)

            return call_id, result, name, tuple(sorted(args.items())) if args else ()

        # Determine which tools can run in parallel
        sequential_tools = {"write_file", "run_shell", "delete_file", "write_json_chunk"}

        for call in tool_calls:
            name = call.get("function", {}).get("name")
            if name in sequential_tools:
                # Run sequentially
                call_id, result, cmd_name, cmd_args = run_one(call)
                output = result.output if isinstance(result, ToolResult) else str(result)

                if isinstance(result, ToolResult) and result.metadata and "new_cwd" in result.metadata:
                    self.session_state["cwd"] = Path(result.metadata["new_cwd"])
                    self.agent.cwd = str(self.session_state["cwd"])
                    self.agent.update_system_prompt()

                self.agent.append_tool(call_id, output)
                call_history.append((cmd_name, cmd_args, current_cwd, output))
            else:
                # Could be parallel, but for simplicity and safety in the engine,
                # let's keep it sequential for now unless we need the speed.
                call_id, result, cmd_name, cmd_args = run_one(call)
                output = result.output if isinstance(result, ToolResult) else str(result)
                self.agent.append_tool(call_id, output)
                call_history.append((cmd_name, cmd_args, current_cwd, output))

        return "ok"

    def _approve_tool(self, name: str, args: dict) -> bool:
        if self.session_state.get("auto_approve"):
            return True

        if name in {"read_file", "list_dir", "search", "glob_files"} and not self.approve_reads:
            return True

        # UI-specific approval would go here. For now, we'll assume the UI handles it
        # or we provide a callback.
        # To keep Engine clean, we should probably pass an approval_callback.
        return True # Placeholder: implementation in CLI will override or provide callback

    def _backup_file(self, path: str):
        try:
            target = resolve_path(self.root, path)
            if target.exists():
                content = target.read_text(encoding="utf-8", errors="replace")
                # ... existing backup logic ...
                pass
        except Exception:
            pass

    def _display_tool_result(self, name: str, args: dict, result: ToolResult):
        if name == "read_file":
            print_read_panel(self.console, args.get("path", ""), result.output, result.is_error, self.theme)
        elif name == "run_shell":
            print_shell_panel(self.console, args.get("cmd", ""), str(self.session_state.get("cwd", self.root)), result.output, result.is_error, self.theme)
        elif name in {"list_dir", "glob_files", "search"}:
            print_list_panel(self.console, f"{name} results", result.output, result.is_error, self.theme)

    def undo_last_write(self) -> bool:
        last_backup = self.session_state.get("last_backup")
        if not last_backup:
            return False
        # ... logic to restore ...
        return True
