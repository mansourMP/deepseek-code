from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich import box
from rich.markup import escape
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.shortcuts import PromptSession, prompt as ptk_prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from rich.prompt import Confirm
from rich.status import Status
from rich.spinner import SPINNERS

from .agent import AgentSettings, DeepSeekAgent
from .config import Config
from .logging_utils import ConversationLogger
from .safety import SandboxError, effective_denylist, resolve_path
from .tools import ToolResult, dispatch_tool, parse_tool_arguments
from .tokens import count_message_tokens
from . import __version__


PROMPT = "[cyan]❯[/] "
PROMPT_PTK = "\x1b[36m❯\x1b[0m "  # Cyan (36) instead of blue (34)
PLACEHOLDER_TEXT = "Type your message or @path/to/file"
SPINNER_NAME = "dots"
STATUS_TEXTS = ["Thinking..."]  # Simple, clean, professional

COMMANDS = {
    "/help": "Show commands",
    "/exit": "Exit",
    "/clear": "Clear conversation",
    "/new": "Start a new chat session",
    "/status": "Show session status",
    "/model": "Change model (interactive or by name)",
    "/tools": "Toggle tools (/tools on|off)",
    "/mode": "Set mode (/mode safe|standard|agent|plan|readonly)",
    "/intro": "Show welcome screen and setup",
    "/theme": "Change theme interactively",
    "/approvals": "Choose approval mode interactively",
    "/approve-reads": "Toggle read approvals (/approve-reads on|off)",
    "/undo": "Undo last file write",
    "/approve": "Toggle auto-approve (/approve on|off)",
    "/safe": "Enable safe mode",
    "/readonly": "Enable read-only mode",
    "/history": "Show recent conversation",
    "/debug": "Toggle debug (/debug on|off)",
}


class CommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.strip()
        if not text.startswith("/"):
            return
        for name, desc in COMMANDS.items():
            if name.startswith(text):
                display = f"{name}  {desc}"
                yield Completion(name, start_position=-len(text), display=display)


class NonEmptyValidator(Validator):
    def validate(self, document) -> None:
        if not document.text.strip():
            raise ValidationError(message="", cursor_position=0)


def _print_help(console: Console) -> None:
    """Show all available commands in a beautiful table."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        pad_edge=False,
    )
    table.add_column("Command", style="cyan", no_wrap=True, width=20)
    table.add_column("Description", style="dim")
    
    for name, desc in sorted(COMMANDS.items()):
        # Remove the leading / for display
        cmd_name = name[1:] if name.startswith("/") else name
        table.add_row(cmd_name, desc)
    
    console.print(table)


def _print_command_hints(console: Console, prefix: str) -> None:
    matches = [name for name in COMMANDS if name.startswith(prefix)]
    if not matches:
        console.print("[yellow]Unknown command. Use /help[/]")
        return
    console.print(f"[dim]Commands:[/dim] {', '.join(matches)}")


def _list_models(console: Console, api_key: str, base_url: str) -> None:
    url = f"{base_url}/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        console.print(f"[red]Model list error[/]: {exc}")
        return
    except httpx.RequestError as exc:
        console.print(f"[red]Network error[/]: {exc}")
        return
    models = [item.get("id", "") for item in data.get("data", []) if item.get("id")]
    if not models:
        console.print("[yellow]No models returned[/]")
        return
    for model in sorted(models):
        console.print(f"  {model}")


def _print_status(
    console: Console,
    root: Path,
    model_name: str,
    auto_approve: bool,
    stream_delay: int,
    tools_enabled: bool,
    mode: str,
    approve_reads: bool,
    readonly: bool,
    debug: bool,
    messages: List[Dict[str, Any]],
    max_context: int,
) -> None:
    """Print the session status in a beautiful box."""
    import uuid
    from rich.panel import Panel
    from rich import box
    
    # Calculate usage
    used_tokens = count_message_tokens(messages, model_name)
    percent = int((used_tokens / max_context) * 100)
    left_percent = 100 - percent
    
    # Progress bars
    def make_bar(pct):
        blocks = int(pct / 5)
        return f"[{'█' * blocks}{'░' * (20 - blocks)}]"

    # Determine status labels
    if mode == "safe":
        approval_status = "Read-Only (Safety)"
        sandbox_status = "Strict"
    elif mode == "plan":
        approval_status = "Plan Mode"
        sandbox_status = "Read-Only"
    elif readonly:
        approval_status = "Read-Only"
        sandbox_status = "Read-Only"
    elif auto_approve:
        approval_status = "Auto-Approve"
        sandbox_status = "Agent"
    else:
        approval_status = "On-Request"
        sandbox_status = "Standard"
        
    # Get session ID (reuse from agent if available, or generate for display)
    session_id = getattr(console, "_session_id", None)
    if not session_id:
        session_id = str(uuid.uuid4())
        console._session_id = session_id  # type: ignore

    content = f"""
 [bold]DeepSeek Code[/] (v{__version__})

 [dim]Visit https://platform.deepseek.com for rate limits and credits[/]

 Model:            [bold cyan]{model_name}[/]
 Directory:        {root}
 Approval:         {approval_status}
 Sandbox:          {sandbox_status}
 Mode:             {mode.title()}
 Session:          {session_id}

 Context window:   {left_percent}% left ({used_tokens:,} used / {max_context:,})
 5h limit:         [bold green]{make_bar(97)}[/] 97% left (mock)
 Weekly limit:     [bold yellow]{make_bar(33)}[/] 33% left (mock)
"""
    
    console.print(Panel(
        content.strip(),
        box=box.ROUNDED,
        expand=False,
        border_style="dim",
        width=80
    ))


def _print_banner(
    console: Console,
    root: Path,
    model: str,
    auto: bool,
    delay_ms: int,
    tools_on: bool,
    mode: str,
    approve_reads: bool,
    readonly_mode: bool,
) -> None:
    # Minimalist header
    pass  # We don't print a huge banner on resize anymore, keeping it clean


def _print_welcome(console: Console, root: Path, model: str, mode: str) -> None:
    """Print the welcome screen with ASCII art."""
    from rich.align import Align
    
    ascii_art = r"""
   [bold cyan]   ____                  _____            __       [/]
   [bold cyan]  / __ \___  ___  ____  / ___/___  ___  / /__     [/]
   [bold cyan] / / / / _ \/ _ \/ __ \ \__ \/ _ \/ _ \/ //_/     [/]
   [bold cyan]/ /_/ /  __/  __/ /_/ /___/ /  __/  __/ ,<        [/]
   [bold cyan]/_____/\___/\___/ .___//____/\___/\___/_/|_|       [/]
   [bold cyan]               /_/                                [/]
             [dim]DeepSeek Code - Intelligent Terminal Agent[/]
    """
    
    console.print(Align.center(ascii_art.strip(), vertical="middle"))
    console.print("")
    
    # Status line
    status = f"[dim]Working in:[/] {root}\n[dim]Model:[/] {model} ({mode})\n[dim]Type /help for commands.[/]"
    console.print(Align.center(status))
    console.print("")
    console.print("[bold white]How can I assist you today?[/]")
    console.print("")


def _start_status_rotator(status: Status, stop_event: threading.Event) -> threading.Thread:
    def _run() -> None:
        idx = 0
        while not stop_event.is_set():
            text = Text(STATUS_TEXTS[idx % len(STATUS_TEXTS)], style="bright_cyan")
            status.update(text)
            idx += 1
            time.sleep(0.6)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def _should_approve(auto_approve: bool, approval_mode: str) -> bool:
    return auto_approve or approval_mode.lower() == "auto"


def _read_key(prompt_text: str, mapping: Dict[str, str]) -> str:
    kb = KeyBindings()
    
    def _bind(key: str, value: str) -> None:
        @kb.add(key)
        def _(event) -> None:
            event.app.exit(result=value)

    # Bind mapped keys
    for key, value in mapping.items():
        if key:
            _bind(key, value)
            
    # Default escape behavior if not explicitly mapped
    if "escape" not in mapping:
        _bind("escape", "escape")
        
    return ptk_prompt(prompt_text, key_bindings=kb, default="")


def _approve(console: Console, prompt: str, session_state: Dict[str, Any], cmd_hint: str = "", cwd: str = "") -> bool:
    if session_state.get("auto_approve"):
        return True
    
    from .ui.approval import confirm_action
    
    context = ""
    if cmd_hint:
        context = f"[bold white]{cmd_hint}[/]\n[dim]in {cwd}[/]"
        
    choice = confirm_action(console, prompt, context)
    
    if choice == "always":
        session_state["auto_approve"] = True
        console.print("  [dim green]✓ Always allowed for this session[/]")
        return True
    if choice == "allow":
        return True
    
    console.print("  [dim red]✗ Action denied[/]")
    return False


def _tool_style(name: str) -> str:
    if name in {"read_file", "list_dir", "search"}:
        return "dim white"
    if name == "write_file":
        return "dim green"
    if name == "delete_file":
        return "dim red"
    return "dim yellow"


def _diff_preview(before: str, after: str) -> List[str]:
    import difflib

    return list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def _diff_summary(diff_lines: List[str]) -> str:
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return f"+{added} -{removed}"


def _edit_content(console: Console, content: str) -> str:
    editor = os.getenv("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        path = handle.name
    try:
        result = subprocess.run([editor, path], check=False)
        if result.returncode != 0:
            console.print("[yellow]Editor exited with non-zero status; keeping original[/]")
            return content
        return Path(path).read_text(encoding="utf-8", errors="replace")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _ensure_backup(root: Path, path: str, content: str) -> Path:
    target = resolve_path(root, path)
    rel = target.relative_to(root)
    backup_root = root / ".deepseek-code" / "backups" / rel
    backup_root.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_root.parent / f"{backup_root.name}.{stamp}.bak"
    backup_path.write_text(content, encoding="utf-8")
    backups = sorted(
        backup_root.parent.glob(f"{backup_root.name}.*.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for extra in backups[10:]:
        try:
            extra.unlink()
        except OSError:
            pass
    return backup_path


def _print_diff_panel(console: Console, path: str, diff_lines: List[str]) -> None:
    table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
    table.add_column("Line", style="dim cyan", justify="right", width=4, no_wrap=True)
    table.add_column("M", justify="center", width=1)
    table.add_column("Code", style="white", ratio=1)

    current_old = 0
    current_new = 0
    has_content = False

    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            try:
                parts = line.split()
                old_part = parts[1][1:]
                new_part = parts[2][1:]
                current_old = int(old_part.split(',')[0])
                current_new = int(new_part.split(',')[0])
            except (ValueError, IndexError):
                pass
            if has_content:
                table.add_row("...", " ", "[dim]...[/]")
            continue

        has_content = True
        if line.startswith("-"):
            table.add_row(str(current_old), "-", f"[red]{line[1:]}[/]")
            current_old += 1
        elif line.startswith("+"):
            table.add_row(str(current_new), "+", f"[green]{line[1:]}[/]")
            current_new += 1
        elif line.startswith(" "):
            table.add_row(str(current_old), " ", f"[dim]{line[1:]}[/]")
            current_old += 1
            current_new += 1

    panel = Panel(
        table,
        title=f"Edit {path}",
        border_style="blue",
        padding=(0, 0),
        box=box.ROUNDED
    )
    console.print(panel)


def _confirm_write(console: Console, path: str, before: str, after: str, session_state: Dict[str, Any]) -> tuple[bool, str]:
    if session_state.get("auto_approve"):
        return True, after

    from .ui.approval import confirm_write
    
    while True:
        diff_lines = _diff_preview(before, after)
        summary = _diff_summary(diff_lines)
        
        if diff_lines:
            _print_diff_panel(console, path, diff_lines)
        else:
            console.print(Panel("(No visible changes)", title=f"Edit {path}", border_style="blue"))

        choice = confirm_write(console, path)
        
        if choice == "diff":
            # Show simple text diff if user wants full view
            for line in diff_lines:
                console.print(line)
            continue
        if choice == "edit":
            after = _edit_content(console, after)
            continue
        if choice == "always":
            session_state["auto_approve"] = True
            console.print("  [dim green]✓ Always allowed for this session[/]")
            return True, after
        if choice == "allow":
            return True, after
        
        console.print("  [dim red]✗ Action denied[/]")
        return False, after


def _print_read_panel(console: Console, path: str, result: ToolResult) -> None:
    status_color = "green" if not result.is_error else "red"
    icon = "✓" if not result.is_error else "✗"
    
    title = f"[{status_color}]{icon}[/]  ReadFile [bold]{escape(path)}[/]"
    
    output = result.output
    # Calculate simple stats
    line_count = len(output.splitlines())
    size_kb = len(output) / 1024
    
    # Truncate strictly for display if too long
    if len(output) > 2000:
        preview = output[:2000] + "\n... (truncated for display) ..."
        display_range = f"Read first {len(preview.splitlines())} lines (total {line_count} lines, {size_kb:.1f}KB)"
    else:
        preview = output
        display_range = f"Read all {line_count} lines ({size_kb:.1f}KB)"

    body = Text()
    body.append(f"{preview}\n\n", style="white")
    body.append(f"[dim]{display_range} from {escape(path)}[/]", style="dim white")

    panel = Panel(
        body,
        title=title,
        title_align="left",
        border_style="dim white",
        box=box.ROUNDED,
        expand=True
    )
    console.print(panel)


def _print_shell_panel(console: Console, cmd: str, cwd: str, result: ToolResult) -> None:
    status_color = "green" if not result.is_error else "red"
    icon = "✓" if not result.is_error else "✗"
    
    title = f"[{status_color}]{icon}[/]  Shell [bold]{escape(cmd)}[/]"
    
    output = result.output.strip()
    if not output:
        output = "(no output)"
        
    # Truncate for display
    if len(output) > 2000:
        preview = output[:2000] + "\n... (truncated)"
    else:
        preview = output
    
    body = Text()
    body.append(f"{preview}\n\n", style="white")
    body.append(f"[dim]Executed in {escape(cwd)}[/]", style="dim white")
    
    panel = Panel(
        body,
        title=title,
        title_align="left",
        border_style="dim white",
        box=box.ROUNDED,
        expand=True
    )
    console.print(panel)


def _print_list_panel(console: Console, title_text: str, result: ToolResult) -> None:
    status_color = "green" if not result.is_error else "red"
    icon = "✓" if not result.is_error else "✗"
    
    title = f"[{status_color}]{icon}[/]  {title_text}"
    
    output = result.output.strip()
    if not output:
        output = "(empty)"
    
    # Format list output cleanly
    # If it's a long list, truncate middle
    lines = output.splitlines()
    if len(lines) > 20:
        preview = "\n".join(lines[:10]) + "\n... (truncated) ...\n" + "\n".join(lines[-5:])
        count_str = f"({len(lines)} items)"
    else:
        preview = output
        count_str = ""
        
    body = Text()
    body.append(f"{preview}\n", style="white")
    if count_str:
        body.append(f"[dim]{count_str}[/]", style="dim white")
    
    panel = Panel(
        body,
        title=title,
        title_align="left",
        border_style="dim white",
        box=box.ROUNDED,
        expand=True
    )
    console.print(panel)


def _run_tool(
    console: Console,
    root: Path,
    name: str,
    arguments: Dict[str, Any],
    denylist: List[str],
    session_state: Dict[str, Any],
    debug: bool,
    approve_reads: bool,
    last_backup: Dict[str, str],
    readonly_mode: bool,
    chunk_file: str | None,
    cwd: Path | None = None,
) -> ToolResult:
    # Only show tool execution in debug mode for clean output
    # Always show tool execution clearly (User needs to know what is happening!)
    style = _tool_style(name)
    desc = name
    if name == "read_file":
        desc = f"Reading [bold cyan]{arguments.get('path', 'file')}[/]"
    elif name == "write_file":
        desc = f"Writing to [bold green]{arguments.get('path', 'file')}[/]"
    elif name == "list_dir":
        desc = f"Listing [bold cyan]{arguments.get('path') or 'current directory'}[/]"
    elif name == "search":
        desc = f"Searching for '[bold cyan]{arguments.get('pattern', '')}[/]'"
    elif name == "glob_files":
        desc = f"Globbing [bold cyan]{arguments.get('pattern', '')}[/]"
    elif name == "run_shell":
        cmd = arguments.get('cmd', '')
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        desc = f"Running: [bold yellow]{cmd}[/]"
    elif name == "read_json_chunk":
        desc = f"Reading chunk from {arguments.get('path')}"
    elif name == "write_json_chunk":
        desc = f"Writing chunk to {arguments.get('path')}"
    elif name == "delete_file":
        desc = f"Deleting [bold red]{arguments.get('path')}[/]"
    
    # Print appropriate icon
    icon = "❯"
    if name in {"write_file", "delete_file"}:
        icon = "✎"
    elif name == "run_shell":
        icon = "⚡"
    elif name == "search":
        icon = "🔍"
    elif name in {"list_dir", "glob_files"}:
        icon = "📂"
        
    console.print(f"[dim]{icon}[/] {desc}")
    
    # Enforce strict directory confinement
    if "path" in arguments:
        try:
            target = resolve_path(root, arguments["path"])
            # Ensure target is within root or is explicitly safe
            # For now, just confirming it resolves correctly and relative to root is usually handled by resolve_path
            # But let's verify if the user is worried about "mother file" (parent dirs)
            if not str(target.resolve()).startswith(str(root.resolve())):
                # If trying to access outside root
                console.print(f"[yellow]⚠️  Warning: Agent trying to access path outside root: {target}[/]")
                # We could block it here if strict sandbox is desired
                # For now, vivid warning is key
        except Exception:
            pass
    
    if chunk_file and name not in {"read_json_chunk", "write_json_chunk"}:
        return ToolResult("Chunk mode restricts tools to read_json_chunk/write_json_chunk", is_error=True, denied=True)
    if name in {"read_file", "list_dir", "search", "glob_files"} and approve_reads:
        hint = arguments.get('path') or arguments.get('pattern') or ""
        approved = _approve(console, f"Allow execution of: '{name}'?", session_state, cmd_hint=hint, cwd=str(cwd or root))
        if not approved:
            return ToolResult("DENIED", is_error=True, denied=True)
    if readonly_mode and name in {"write_file", "run_shell", "delete_file"}:
        return ToolResult("Read-only mode enabled", is_error=True, denied=True)
    if name == "delete_file":
        approved = _approve(console, f"Allow deletion of: '{arguments.get('path')}'?", session_state, cwd=str(cwd or root))
        if not approved:
            return ToolResult("DENIED", is_error=True, denied=True)
    if name == "write_file":
        target = resolve_path(root, arguments["path"])
        before = ""
        if target.exists():
            before = target.read_text(encoding="utf-8", errors="replace")
        after = arguments.get("content", "")
        approved, after = _confirm_write(console, arguments["path"], before, after, session_state)
        if not approved:
            return ToolResult("DENIED", is_error=True, denied=True)
        arguments["content"] = after
        if target.exists():
            backup_path = _ensure_backup(root, arguments["path"], before)
            last_backup["path"] = str(target)
            last_backup["backup"] = str(backup_path)
    if name == "run_shell":
        approved = _approve(console, "Allow execution of shell command?", session_state, cmd_hint=arguments.get('cmd'), cwd=str(cwd or root))
        if not approved:
            return ToolResult("DENIED", is_error=True, denied=True)
            
    result = dispatch_tool(root, name, arguments, denylist, cwd)
    
    if name == "run_shell":
        _print_shell_panel(console, arguments.get('cmd', ''), str(cwd or root), result)
    elif name == "read_file":
        _print_read_panel(console, arguments.get('path', ''), result)
    elif name in {"list_dir", "glob_files"}:
        _print_list_panel(console, f"{name} results", result)
        
    return result


def _handle_tool_calls(
    console: Console,
    agent: DeepSeekAgent,
    root: Path,
    tool_calls: List[Dict[str, Any]],
    denylist: List[str],
    session_state: Dict[str, Any],
    debug: bool,
    approve_reads: bool,
    last_backup: Dict[str, str],
    readonly_mode: bool,
    chunk_state_path: Path | None,
    chunk_file: str | None,
) -> str:
    import concurrent.futures
    
    # Initialize history if missing
    if "call_history" not in session_state:
        session_state["call_history"] = []
        
    call_history = session_state["call_history"]
    current_cwd = str(session_state.get("cwd", root))
    
    # Extract current calls with normalized args
    current_calls = []
    for call in tool_calls:
        func = call.get("function", {})
        name = func.get("name")
        raw_args = func.get("arguments", "")
        args, _ = parse_tool_arguments(raw_args)
        # Sort args for stable comparison
        arg_tuple = tuple(sorted(args.items())) if args else ()
        current_calls.append((name, arg_tuple, current_cwd, call.get("id")))

    # Loop Detection using Sliding Window
    # Check if any of the current calls have appeared recently IN THE SAME CONTEXT
    loop_detected = False
    cached_response_map = {}
    
    for name, arg_tuple, cwd, call_id in current_calls:
        # Check occurrence count in last 10 turns (approx 20-30 calls)
        # We store (name, arg_tuple, cwd, output) in history
        matches = [
            entry for entry in call_history[-20:] 
            if entry[0] == name and entry[1] == arg_tuple and entry[2] == cwd
        ]
        
        if len(matches) >= 1: # Strict: warn on FIRST repetition in same CWD
            loop_detected = True
            # Get the last output for this call
            last_output = matches[-1][3]
            cached_response_map[call_id] = last_output

    if loop_detected:
        session_state["failed_attempts"] = session_state.get("failed_attempts", 0) + 1
        console.print(f"[bold red]⟳ Environment: Loop detected ({session_state['failed_attempts']}/3)[/]")
        
        # DUMP BRAIN
        try:
            dump_path = root / "debug_history.json"
            dump_path.write_text(json.dumps(agent.messages, indent=2, default=str), encoding="utf-8")
            console.print(f"[dim]Debug history dumped to {dump_path}[/]")
        except Exception as e:
            console.print(f"[dim red]Failed to dump history: {e}[/]")
        
        if session_state["failed_attempts"] >= 3:
            for call in tool_calls:
                 agent.append_tool(
                    call.get("id"),
                    "SYSTEM INTERVENTION: You are looping indefinitely. Stop. Ask the user for clarification."
                )
            return "intervene"
        else:
            # Return cached results or warnings
            for i, call in enumerate(tool_calls):
                call_id = call.get("id")
                name = call.get("function", {}).get("name")
                
                if call_id in cached_response_map:
                    cached = cached_response_map[call_id]
                    
                    hint = "Do not run it again. Move to the next step."
                    if name in {"list_dir", "glob_files", "search"}:
                        hint = "You already have this file list. STOP searching and PROCEED to read the files you found (e.g. read_file)."
                    
                    msg = f"ENVIRONMENT ALERT: You just ran '{name}' with these exact arguments in this directory. Here is the cached result:\n{cached}\n\n{hint}"
                    agent.append_tool(call_id, msg)
                else:
                     agent.append_tool(call_id, "LOOP ALERT: Parallel sibling command blocked due to loop detection.")
            return "ok"
    else:
        session_state["failed_attempts"] = 0

    
    # Execute tools
    outputs = [None] * len(tool_calls) 
    
    # Helper to run a single tool call
    def run_one(index, call):
        call_id = call.get("id")
        func = call.get("function", {})
        name = func.get("name")
        raw_args = func.get("arguments", "")
        
        if not name:
            return index, call_id, "ERROR: missing function name", None, None
            
        args, error = parse_tool_arguments(raw_args)
        if error or args is None:
            return index, call_id, f"ERROR: {error}", name, None

        arg_tuple = tuple(sorted(args.items())) if args else ()

        result = _run_tool(
            console,
            root,
            name,
            args,
            denylist,
            session_state,
            debug,
            approve_reads,
            last_backup,
            readonly_mode,
            chunk_file,
            cwd=session_state.get("cwd", root)
        )
        
        return index, call_id, result, name, arg_tuple

    sequential_tools = {"write_file", "run_shell", "delete_file", "write_json_chunk"}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i, call in enumerate(tool_calls):
            name = call.get("function", {}).get("name")
            
            if name in sequential_tools:
                # Run sequentially
                idx, call_id, result, cmd_name, cmd_args = run_one(i, call)
                
                if isinstance(result, ToolResult) and result.denied:
                     agent.append_tool(call_id, "ERROR: DENIED")
                     return "denied"

                output_str = ""
                if isinstance(result, str):
                    output_str = result
                else:
                    if result.metadata and "new_cwd" in result.metadata:
                        session_state["cwd"] = Path(result.metadata["new_cwd"])
                        agent.cwd = str(session_state["cwd"])
                        agent.update_system_prompt()
                    output_str = result.output

                agent.append_tool(call_id, output_str)
                # Add to history
                call_history.append((cmd_name, cmd_args, current_cwd, output_str))
            else:
                # Queue parallel
                futures.append(executor.submit(run_one, i, call))
        
        # Process parallel results
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, call_id, result, cmd_name, cmd_args = future.result()
                
                output_str = ""
                if isinstance(result, str):
                    output_str = result
                elif hasattr(result, "output"):
                     output_str = result.output
                else:
                     output_str = str(result)
                
                agent.append_tool(call_id, output_str)
                # Add to history
                if cmd_name:
                    call_history.append((cmd_name, cmd_args, current_cwd, output_str))
                    
            except Exception as e:
                console.print(f"[red]Parallel execution error: {e}[/]")
    
    # Trim history to keep memory usage low
    if len(call_history) > 50:
        session_state["call_history"] = call_history[-50:]
                
    return "ok"


def _select_mode_interactive(console: Console, current_mode: str) -> str | None:
    """Show a professional interactive mode selector."""
    from .ui.approval import InteractiveMenu
    
    options = [
        {
            "label": "Safe (Read Only)",
            "value": "safe", 
            "description": "Requires approval to edit files and run commands."
        },
        {
            "label": "Standard",
            "value": "standard",
            "description": "Standard mode with manual approvals."
        },
        {
            "label": "Agent (Auto-Approve)",
            "value": "agent",
            "description": "Read and edit files, and run commands automatically."
        },
        {
            "label": "Plan Mode",
            "value": "plan",
            "description": "Read-only exploration and planning."
        },
    ]
    
    # Pre-select the current mode if possible
    menu = InteractiveMenu("Select Operation Mode", options, console)
    
    # Find index of current mode
    for i, opt in enumerate(options):
        if opt["value"] == current_mode:
            menu.selected_index = i
            break
            
    result = menu.show()
    return result if result != "deny" else None


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--model", default=None, help="Override model (default: DEEPSEEK_MODEL or deepseek-chat)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--log", "log_to_file", is_flag=True, help="Write conversation log to .deepseek-code.log")
@click.option("--auto-approve", is_flag=True, help="Auto-approve file writes and shell commands")
@click.option("--word-delay", type=int, default=None, help="Delay per word in ms for streaming output")
@click.option("--max-context", type=int, default=None, help="Max context tokens for display")
@click.option("--timestamps/--no-timestamps", default=None, help="Show timestamps")
@click.option("--mode", type=click.Choice(["safe", "standard", "agent", "readonly"], case_sensitive=False), default=None, help="Agent mode")
@click.option("--approve-reads", is_flag=True, help="Require approval for reads/list/search")
@click.option("--file", "chunk_file", type=str, default=None, help="JSON file to edit in chunks")
@click.option("--start", "chunk_start", type=int, default=None, help="Start index for chunk")
@click.option("--count", "chunk_count", type=int, default=None, help="Number of items to load")
@click.option("--state", "chunk_state", type=str, default=None, help="State file for resume")
@click.version_option(__version__)
def main(
    model: str | None,
    debug: bool,
    log_to_file: bool,
    auto_approve: bool,
    word_delay: int | None,
    max_context: int | None,
    timestamps: bool | None,
    mode: str | None,
    approve_reads: bool,
    chunk_file: str | None,
    chunk_start: int | None,
    chunk_count: int | None,
    chunk_state: str | None,
) -> None:
    console = Console(force_terminal=True)
    
    # Set up Ctrl+C handler for graceful interruption
    interrupted = threading.Event()
    
    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully."""
        if not interrupted.is_set():
            interrupted.set()
            console.print("\n[yellow]⚠ Interrupted by user[/]")
            console.print("[dim]Press Ctrl+C again to force quit[/]")
        else:
            console.print("\n[red]Force quitting...[/]")
            sys.exit(130)  # Standard exit code for SIGINT
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if SPINNER_NAME not in SPINNERS:
        SPINNERS[SPINNER_NAME] = {
            "interval": 80,
            "frames": SPINNER_FRAMES,
            "description": "DeepSeek pulse",
        }
    
    # Use project root as sandbox root to allow access to parent dirs
    from .safety import find_project_root
    from dotenv import load_dotenv
    
    root = find_project_root(Path.cwd())
    load_dotenv(root / ".env")
    
    config = Config.load(root)
    if log_to_file:
        config.log_path = root / ".deepseek-code.log"
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        console.print("[red]Missing DEEPSEEK_API_KEY[/]")
        sys.exit(1)

    model_name = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    logger = ConversationLogger(config.log_path) if config.log_path else None
    delay_ms = config.stream_word_delay_ms if word_delay is None else word_delay
    max_context_tokens = max_context or int(os.getenv("DEEPSEEK_MAX_CONTEXT", config.max_context_tokens))
    show_timestamps = config.show_timestamps if timestamps is None else timestamps
    selected_mode = (mode or config.mode).lower()
    
    # Handle different modes
    if selected_mode == "readonly":
        tools_enabled = True
        readonly_mode = True
        plan_mode = False
    elif selected_mode == "plan":
        tools_enabled = True
        readonly_mode = True  # Plan mode is read-only during exploration
        plan_mode = True
    else:
        tools_enabled = selected_mode in {"standard", "agent"}
        readonly_mode = bool(config.readonly)
        plan_mode = False
    
    auto = auto_approve or _should_approve(config.auto_approve, config.approval_mode)
    if selected_mode == "agent":
        auto = True
    settings = AgentSettings(
        api_key=api_key,
        model=model_name,
        max_messages=config.max_messages,
        stream_word_delay_ms=delay_ms,
        max_context_tokens=max_context_tokens,
        indent_assistant=config.indent_assistant,
        assistant_indent=config.assistant_indent,
        debug=debug,
        logger=logger,
        system_prompt=config.get_system_prompt(),
        append_system_prompt=config.append_system_prompt,
    )
    agent = DeepSeekAgent(settings, console, cwd=str(root))
    
    if debug:
        console.print("[bold yellow]DEBUG: System Prompt:[/]")
        console.print(agent.messages[0]["content"])
    elif config.get_system_prompt() is None:
        # Confirm we are using the internal high-performance prompt
        console.print("[dim]✓ Silent Mode Active (High-Performance)[/]")

    denylist = effective_denylist(config.denylist)
    session_state = {
        "auto_approve": auto,
        "cwd": root,  # Initialize CWD
    }
    approve_reads_enabled = approve_reads or config.approve_reads
    generated_plan = None  # Store the generated plan
    last_backup: Dict[str, str] = {}
    chunk_start_index = chunk_start or 0
    chunk_state_path = Path(chunk_state) if chunk_state else None
    if chunk_state_path and chunk_state_path.exists():
        try:
            data = json.loads(chunk_state_path.read_text(encoding="utf-8"))
            chunk_start_index = int(data.get("last_index", chunk_start_index))
        except json.JSONDecodeError:
            console.print("[yellow]Invalid state file; ignoring[/]")
    if chunk_file and chunk_count is None:
        console.print("[red]--count is required with --file[/]")
        sys.exit(1)
    if chunk_file:
        agent.reset()
        agent.append(
            "system",
            (
                "Chunked JSON mode enabled. Use read_json_chunk and write_json_chunk only. "
                "Never call read_file/list_dir/search/run_shell. "
                f"Target file: {chunk_file}. Start: {chunk_start_index}. Count: {chunk_count}. "
                "Do not read the full file. Only edit the provided slice and write it back."
            ),
        )
    _print_welcome(console, root, model_name, selected_mode)
    _print_banner(
        console,
        root,
        model_name,
        auto,
        delay_ms,
        tools_enabled,
        selected_mode,
        approve_reads_enabled,
        readonly_mode,
    )
    last_width = console.size.width

    def _right_prompt() -> HTML:
        return HTML("")

    def _prompt_text() -> ANSI:
        # Prompt is just the chevron because status is shown above
        return ANSI(PROMPT_PTK)

    session = PromptSession(
        completer=CommandCompleter(),
        complete_while_typing=True,
        history=InMemoryHistory(),
        validator=NonEmptyValidator(),
        validate_while_typing=False,
        placeholder=HTML("<ansigray>Type your message or @path/to/file</ansigray>"),
        style=Style.from_dict(
            {
                "prompt": "ansigray",
                "": "ansiwhite",
            }
        ),
    )

    def _bottom_toolbar():
        """Create persistent bottom toolbar."""
        model_name = agent.settings.model
        used = count_message_tokens(agent.messages, agent.settings.model)
        total = max(agent.settings.max_context_tokens, 1)
        left = max(total - used, 0)
        percent = int((left / total) * 100)
        
        # Format similar to Codex/Gemini: Project | Model | Context
        # Using ANSI colors via prompt_toolkit's HTML
        return HTML(
            f"<ansigray>{root.name}</ansigray> <ansicyan>│</ansicyan> "
            f"<b>{model_name}</b> <ansicyan>│</ansicyan> "
            f"<ansigray>{percent}% context</ansigray>"
        )

    while True:
        try:
            # Reset interruption flag for each new turn
            interrupted.clear()
            console.print("")
            
            # Get input with clean prompt and persistent toolbar
            user_input = session.prompt(
                _prompt_text(),
                rprompt=_right_prompt,
                bottom_toolbar=_bottom_toolbar
            ).strip()
            
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            return
        if console.size.width != last_width:
            last_width = console.size.width
            _print_banner(
                console,
                root,
                model_name,
                auto,
                delay_ms,
                tools_enabled,
                selected_mode,
                approve_reads_enabled,
                readonly_mode,
            )
        if not user_input:
            continue
        if user_input == "/exit":
            console.print("[dim]Goodbye.[/]")
            return
        # Show help menu when typing just / (like Gemini CLI)
        if user_input == "/" or user_input == "/help":
            _print_help(console)
            continue
        if user_input == "/clear":
            agent.reset()
            console.print("[dim]Conversation cleared.[/]")
            continue
        if user_input == "/new":
            agent.reset()
            import uuid
            console._session_id = str(uuid.uuid4())
            console.print("[bold green]✓[/] Started new session")
            continue
        if user_input == "/intro":
            # Show the grand entrance and theme setup
            _print_welcome(console, root, model_name, selected_mode)
            from .ui.theme_selector import select_theme_interactive
            from .ui.themes import get_theme, set_theme
            
            new_theme = select_theme_interactive(config.theme, console)
            if new_theme:
                config.theme = new_theme
                config.save(root)
                # Apply theme immediately if possible or just notify
                console.print(f"\n[cyan]✓[/] Theme set to [bold]{new_theme}[/]")
            continue
            
        if user_input == "/theme":
            from .ui.theme_selector import select_theme_interactive
            from .ui.themes import get_theme, set_theme
            
            new_theme = select_theme_interactive(config.theme, console)
            if new_theme:
                config.theme = new_theme
                config.save(root)
                console.print(f"\n[cyan]✓[/] Theme set to [bold]{new_theme}[/]")
            continue
            
        if user_input == "/status":
            _print_status(
                console,
                root,
                model_name,
                auto,
                delay_ms,
                tools_enabled,
                selected_mode,
                approve_reads_enabled,
                readonly_mode,
                debug,
                agent.messages,
                max_context_tokens,
            )
            continue
        
        # Use new modular command system for /model and /models
        if user_input == "/models" or user_input == "/model":
            from .ui.commands import CommandContext, cmd_models, cmd_model
            from .ui.themes import get_theme
            
            ctx = CommandContext(
                console=console,
                agent=agent,
                root=root,
                model_name=model_name,
                api_key=api_key,
                base_url=settings.base_url,
                theme=get_theme(config.theme),
                auto_approve=auto,
                tools_enabled=tools_enabled,
                readonly_mode=readonly_mode,
                debug=debug,
                approve_reads_enabled=approve_reads_enabled,
                selected_mode=selected_mode,
                delay_ms=delay_ms,
            )
            
            if user_input == "/models":
                cmd_models(ctx, "")
            else:
                cmd_model(ctx, "")
            continue
        
        if user_input.startswith("/model "):
            from .ui.commands import CommandContext, cmd_model
            from .ui.themes import get_theme
            
            # Extract the argument
            parts = user_input.split(maxsplit=1)
            arg = parts[1] if len(parts) == 2 else ""
            
            ctx = CommandContext(
                console=console,
                agent=agent,
                root=root,
                model_name=model_name,
                api_key=api_key,
                base_url=settings.base_url,
                theme=get_theme(config.theme),
                auto_approve=auto,
                tools_enabled=tools_enabled,
                readonly_mode=readonly_mode,
                debug=debug,
                approve_reads_enabled=approve_reads_enabled,
                selected_mode=selected_mode,
                delay_ms=delay_ms,
            )
            
            result = cmd_model(ctx, arg)
            
            # Update model_name if it changed
            if agent.settings.model != model_name:
                model_name = agent.settings.model
            
            continue
        
        if user_input == "/undo":
            if not last_backup:
                console.print("[yellow]No backup available[/]")
                continue
            approved = _approve(console, "Approve undo last write?", auto)
            if not approved:
                console.print("[yellow]Undo cancelled[/]")
                continue
            target = Path(last_backup["path"])
            backup = Path(last_backup["backup"])
            if not backup.exists():
                console.print("[red]Backup missing[/]")
                continue
            target.write_text(backup.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            console.print("[green]Undo complete[/]")
            continue
        
        if user_input.startswith("/tools"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2 and parts[1].lower() in {"on", "off"}:
                tools_enabled = parts[1].lower() == "on"
                console.print(f"Tools {'enabled' if tools_enabled else 'disabled'}")
                _print_banner(
                    console,
                    root,
                    model_name,
                    auto,
                    delay_ms,
                    tools_enabled,
                    selected_mode,
                    approve_reads_enabled,
                    readonly_mode,
                )
            else:
                console.print("Usage: /tools on|off")
            continue
        if user_input.startswith("/mode"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 1:
                # Interactive selection
                new_mode = _select_mode_interactive(console, selected_mode)
                if new_mode:
                    selected_mode = new_mode
                else:
                    console.print("  [dim]Selection cancelled[/]")
                    continue
            elif parts[1].lower() in {"safe", "standard", "agent", "readonly", "plan"}:
                selected_mode = parts[1].lower()
            else:
                console.print("Usage: /mode [safe|agent]")
                continue
                
            # Apply mode changes
            if selected_mode == "safe":
                tools_enabled = False
                readonly_mode = False
                session_state["auto_approve"] = False
            elif selected_mode == "agent":
                tools_enabled = True
                readonly_mode = False
                session_state["auto_approve"] = True
            
            console.print(f"  [cyan]✓[/] Mode set to [bold]{selected_mode}[/]")
            continue
        
        if user_input == "/approvals":
            # Show interactive approval mode selector
            from .ui.approval_selector import select_approval_mode
            
            new_mode = select_approval_mode(selected_mode, console)
            
            if new_mode:
                selected_mode = new_mode
                
                # Set mode-specific flags
                if selected_mode == "plan":
                    tools_enabled = True
                    readonly_mode = True
                    plan_mode = True
                elif selected_mode == "readonly":
                    tools_enabled = True
                    readonly_mode = True
                    plan_mode = False
                elif selected_mode == "safe":
                    tools_enabled = False
                    readonly_mode = False
                    plan_mode = False
                    auto = False
                elif selected_mode == "agent":
                    tools_enabled = True
                    readonly_mode = False
                    plan_mode = False
                    auto = True
                else:  # standard
                    tools_enabled = True
                    readonly_mode = False
                    plan_mode = False
                    auto = auto_approve or _should_approve(config.auto_approve, config.approval_mode)
                
                console.print(f"\n[cyan]✓[/] Mode set to [bold]{selected_mode}[/]")
                _print_banner(
                    console,
                    root,
                    model_name,
                    auto,
                    delay_ms,
                    tools_enabled,
                    selected_mode,
                    approve_reads_enabled,
                    readonly_mode,
                )
            else:
                console.print("\n[dim]Selection cancelled[/]")
            continue
        if user_input.startswith("/approve-reads"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2 and parts[1].lower() in {"on", "off"}:
                approve_reads_enabled = parts[1].lower() == "on"
                console.print(f"Read approvals {'enabled' if approve_reads_enabled else 'disabled'}")
                _print_banner(
                    console,
                    root,
                    model_name,
                    auto,
                    delay_ms,
                    tools_enabled,
                    selected_mode,
                    approve_reads_enabled,
                    readonly_mode,
                )
            else:
                console.print("Usage: /approve-reads on|off")
            continue
        if user_input.startswith("/approve"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2 and parts[1].lower() in {"on", "off"}:
                auto = parts[1].lower() == "on"
                console.print(f"Auto-approve {'enabled' if auto else 'disabled'}")
                _print_banner(
                    console,
                    root,
                    model_name,
                    auto,
                    delay_ms,
                    tools_enabled,
                    selected_mode,
                    approve_reads_enabled,
                    readonly_mode,
                )
            else:
                console.print("Usage: /approve on|off")
            continue
        if user_input == "/safe":
            selected_mode = "safe"
            tools_enabled = False
            readonly_mode = False
            auto = False
            console.print("Mode set to safe")
            _print_banner(
                console,
                root,
                model_name,
                auto,
                delay_ms,
                tools_enabled,
                selected_mode,
                approve_reads_enabled,
                readonly_mode,
            )
            continue
        if user_input == "/readonly":
            selected_mode = "readonly"
            tools_enabled = True
            readonly_mode = True
            auto = False
            console.print("Mode set to readonly")
            _print_banner(
                console,
                root,
                model_name,
                auto,
                delay_ms,
                tools_enabled,
                selected_mode,
                approve_reads_enabled,
                readonly_mode,
            )
            continue
        if user_input == "/history":
            recent = [m for m in agent.messages if m.get("role") in {"user", "assistant"}][-6:]
            if not recent:
                console.print("[yellow]No history[/]")
                continue
            for msg in recent:
                role = msg.get("role", "")
                content = (msg.get("content") or "").strip()
                label = "you" if role == "user" else "assistant"
                console.print(f"{label}: {content[:120]}")
            continue
        if user_input.startswith("/debug"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2 and parts[1].lower() in {"on", "off"}:
                debug = parts[1].lower() == "on"
                agent.settings.debug = debug
                console.print(f"Debug {'enabled' if debug else 'disabled'}")
            else:
                console.print("Usage: /debug on|off")
            continue
        if user_input.startswith("/"):
            _print_command_hints(console, user_input)
            continue

        # Plan mode: Modify the prompt to request a plan
        if plan_mode:
            plan_prompt = f"""{user_input}

IMPORTANT: You are in PLAN MODE. Follow these steps:
1. Explore the codebase using read_file, list_dir, and search tools
2. Analyze the code structure and understand the requirements
3. Create a detailed step-by-step plan in this format:

📋 PLAN:
1. [Step description]
   - [Specific action]
   - [Files involved]
   
2. [Step description]
   - [Specific action]
   - [Files involved]

Do NOT make any changes yet. Only explore and create the plan.
"""
            agent.append("user", plan_prompt)
        else:
            agent.append("user", user_input)
        console.print("")

        # Reset loop detection for new turn
        session_state["failed_attempts"] = 0
        session_state["last_tool"] = None

        attempts = 0
        completed = False
        use_tools = tools_enabled
        while True:
            attempts += 1
            status = Status(Text(STATUS_TEXTS[0], style="bright_cyan"))
            status.start()
            rotator_stop = threading.Event()
            rotator = _start_status_rotator(status, rotator_stop)
            thinking_start = time.perf_counter()
            thinking_seconds: float | None = None

            def _on_stream_start() -> None:
                nonlocal thinking_seconds
                rotator_stop.set()
                status.stop()
                if thinking_seconds is None:
                    thinking_seconds = time.perf_counter() - thinking_start

            try:
                allowed_tools = None
                if chunk_file:
                    allowed_tools = {"read_json_chunk", "write_json_chunk"}
                content, tool_calls = agent.call_model(
                    use_tools=use_tools,
                    on_stream_start=_on_stream_start,
                    allowed_tools=allowed_tools,
                    stop_event=interrupted,
                )
                
                # Check if interrupted during model call
                if interrupted.is_set():
                    rotator_stop.set()
                    status.stop()
                    console.print("[yellow]Operation cancelled[/]")
                    break
            except httpx.HTTPStatusError as exc:
                rotator_stop.set()
                status.stop()
                if exc.response.status_code == 400:
                    # Likely context length exceeded
                    console.print("[yellow]⚠️  Context limit reached. Trimming history and retrying...[/]")
                    agent.trim_messages()
                    # Optionally retry automatically or just let the user know
                    # For now, let's stop and let the user re-prompt or let them see the error if it persists
                    # But actually, trim_messages was likely already called. 
                    # If it's still 400, it might be the system prompt + single message is too big.
                    try:
                         err_json = exc.response.json()
                         msg = err_json.get("error", {}).get("message", "Unknown error")
                         console.print(f"[dim red]{msg}[/]")
                    except Exception:
                         console.print("[dim red]Context too large or bad request.[/]")
                    break
                
                if exc.response.status_code == 401:
                    console.print("[red]Invalid API key[/]")
                    return
                if exc.response.status_code == 429 and attempts < 4:
                    console.print("[yellow]Rate limited, retrying...[/]")
                    agent.backoff_sleep(attempts)
                    continue
                console.print(f"[red]API Error {exc.response.status_code}[/]")
                break
            except httpx.RequestError as exc:
                rotator_stop.set()
                status.stop()
                console.print(f"[red]Network error[/]: {exc}")
                break
            finally:
                rotator_stop.set()
                status.stop()
                if rotator.is_alive():
                    rotator.join(timeout=0.2)

            if tool_calls:
                status.stop()
                agent.append_assistant_with_tools(content, tool_calls)
                status_code = _handle_tool_calls(
                    console,
                    agent,
                    root,
                    tool_calls,
                    denylist,
                    session_state,
                    debug,
                    approve_reads_enabled,
                    last_backup,
                    readonly_mode,
                    chunk_state_path,
                    chunk_file,
                )
                if status_code == "retry":
                    agent.append(
                        "system",
                        "Tool calling failed. Respond with plain text and ReAct-style reasoning without tools.",
                    )
                    use_tools = False
                    continue
                if status_code == "denied":
                    completed = True
                    break
                if status_code == "intervene": # New status to force user input
                    console.print("[bold yellow]Agent requires intervention. Please provide guidance.[/]")
                    completed = True # Break current agent turn, return to user prompt
                    break
                continue
            if content:
                agent.append("assistant", content)
            completed = True
            break
        if completed and config.show_separator:
             pass # Separator removed for cleaner look
        if thinking_seconds is None:
            thinking_seconds = time.perf_counter() - thinking_start
        # Minimal footer
        # console.print(f"[dim]thought: {thinking_seconds:.1f}s[/]")
        console.print("")
