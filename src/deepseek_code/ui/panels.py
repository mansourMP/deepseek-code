"""
Rich panel components for DeepSeek Code terminal interface.

Provides beautiful, consistent panel rendering for diffs, shell output,
status displays, and welcome banners.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .themes import Theme, get_theme

# ═══════════════════════════════════════════════════════════════════════════════
# DIFF PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def diff_preview(before: str, after: str) -> list[str]:
    """Generate unified diff lines."""
    return list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def diff_summary(diff_lines: list[str]) -> tuple[int, int]:
    """Count added and removed lines."""
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return added, removed


def print_diff_panel(
    console: Console,
    path: str,
    diff_lines: list[str],
    theme: Theme | None = None,
) -> None:
    """
    Render a beautiful diff panel with syntax highlighting.

    Features:
    - Line numbers
    - Color-coded additions/deletions
    - Contextual separators for hunks
    - Themed borders
    """
    theme = theme or get_theme()

    # Create table for diff content
    table = Table(
        box=None,
        show_header=False,
        padding=(0, 1),
        expand=True,
        show_edge=False,
    )
    table.add_column("Line", style=f"{theme.dim}", justify="right", width=5, no_wrap=True)
    table.add_column("M", justify="center", width=1)
    table.add_column("Code", ratio=1, overflow="fold")

    current_old = 0
    current_new = 0
    has_content = False
    hunk_count = 0

    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith("@@"):
            hunk_count += 1
            try:
                parts = line.split()
                old_part = parts[1][1:]
                new_part = parts[2][1:]
                current_old = int(old_part.split(',')[0])
                current_new = int(new_part.split(',')[0])
            except (ValueError, IndexError):
                pass

            if has_content:
                # Hunk separator
                table.add_row(
                    "",
                    "",
                    f"[{theme.dim}]{'─' * 40}[/]"
                )
            continue

        has_content = True

        if line.startswith("-"):
            # Removed line
            table.add_row(
                str(current_old),
                f"[{theme.diff_remove}]−[/]",
                f"[{theme.diff_remove}]{escape(line[1:])}[/]"
            )
            current_old += 1

        elif line.startswith("+"):
            # Added line
            table.add_row(
                str(current_new),
                f"[{theme.diff_add}]+[/]",
                f"[{theme.diff_add}]{escape(line[1:])}[/]"
            )
            current_new += 1

        elif line.startswith(" "):
            # Context line
            table.add_row(
                f"[{theme.diff_context}]{current_old}[/]",
                " ",
                f"[{theme.diff_context}]{escape(line[1:])}[/]"
            )
            current_old += 1
            current_new += 1

    # Calculate summary
    added, removed = diff_summary(diff_lines)
    summary_text = f"[{theme.diff_add}]+{added}[/] [{theme.diff_remove}]−{removed}[/]"

    # Create panel
    panel = Panel(
        table,
        title=f"[bold]✏️  {escape(path)}[/]  {summary_text}",
        title_align="left",
        border_style=theme.border_primary,
        padding=(0, 1),
        box=box.ROUNDED,
    )

    console.print(panel)


# ═══════════════════════════════════════════════════════════════════════════════
# SHELL OUTPUT PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def print_shell_panel(
    console: Console,
    command: str,
    cwd: str,
    output: str,
    is_error: bool = False,
    theme: Theme | None = None,
) -> None:
    """
    Render shell command output in a styled panel.

    Features:
    - Success/error status indicator
    - Working directory display
    - Truncated output for long commands
    - Themed styling
    """
    theme = theme or get_theme()

    # Status indicator
    if is_error:
        status_icon = "✗"
        status_color = theme.error
        border_style = theme.border_error
    else:
        status_icon = "✓"
        status_color = theme.success
        border_style = theme.border_success

    # Truncate long commands for display
    display_cmd = command if len(command) <= 60 else command[:57] + "..."

    # Build title
    title = (
        f"[{status_color}]{status_icon}[/]  "
        f"[bold]$ {escape(display_cmd)}[/]  "
        f"[{theme.dim}]({escape(cwd)})[/]"
    )

    # Handle empty output
    content = output.strip() if output.strip() else f"[{theme.dim}](no output)[/]"

    # Truncate very long output
    lines = content.splitlines()
    if len(lines) > 50:
        content = "\n".join(lines[:25] + [f"[{theme.dim}]... ({len(lines) - 50} more lines) ...[/]"] + lines[-25:])

    panel = Panel(
        Text.from_markup(content) if "[" in content else Text(content),
        title=title,
        title_align="left",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )

    console.print(panel)


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def print_status_panel(
    console: Console,
    root: Path,
    model: str,
    mode: str,
    auto_approve: bool,
    tools_enabled: bool,
    readonly_mode: bool,
    debug: bool,
    version: str,
    messages: list[dict[str, Any]],
    max_context: int,
    theme: Theme | None = None,
) -> None:
    """
    Render a detailed session status panel with token usage and progress bars.
    """
    theme = theme or get_theme()

    # Calculate token usage
    from ..tokens import count_message_tokens
    used_tokens = count_message_tokens(messages, model)
    percent_used = (used_tokens / max_context) * 100
    percent_left = 100 - percent_used

    # Progress bar helper
    def make_bar(pct: float, color: str) -> str:
        blocks = int(pct / 5)
        return f"[{color}]{'█' * blocks}{'░' * (20 - blocks)}[/]"

    # Context usage bar color
    context_color = theme.success if percent_left > 30 else (theme.warning if percent_left > 10 else theme.error)

    # Build status indicators
    status_parts = []
    if mode == "safe":
        status_parts.append(f"[{theme.warning}]Safe Mode (Read-Only)[/]")
    elif mode == "plan":
        status_parts.append(f"[{theme.info}]Plan Mode (Read-Only)[/]")
    elif readonly_mode:
        status_parts.append(f"[{theme.warning}]Read-Only Mode[/]")
    elif auto_approve:
        status_parts.append(f"[{theme.success}]Auto-Approve Enabled[/]")
    else:
        status_parts.append(f"[{theme.info}]Standard (Manual Approval)[/]")

    # Session ID (if available)
    session_id = getattr(console, "_session_id", "N/A")

    content = [
        f"[bold {theme.primary}]DeepSeek Code[/] [dim]v{version}[/]",
        "",
        f"[{theme.dim}]Model:[/]       [bold]{model}[/]",
        f"[{theme.dim}]Directory:[/]   {root}",
        f"[{theme.dim}]Session:[/]     {session_id}",
        f"[{theme.dim}]Mode:[/]        {'  '.join(status_parts)}",
        "",
        f"[{theme.dim}]Context Window:[/] {percent_left:.1f}% left ({used_tokens:,} / {max_context:,} tokens)",
        f"{make_bar(percent_left, context_color)}",
    ]

    panel = Panel(
        "\n".join(content),
        border_style=theme.border_secondary,
        box=box.ROUNDED,
        padding=(1, 2),
    )

    console.print(panel)


# ═══════════════════════════════════════════════════════════════════════════════
# WELCOME BANNER
# ═══════════════════════════════════════════════════════════════════════════════

def print_welcome_banner(
    console: Console,
    root: Path,
    model: str,
    mode: str,
    version: str,
    theme: Theme | None = None,
) -> None:
    """
    Render a stunning welcome banner on startup.
    """
    theme = theme or get_theme()

    # ASCII art logo (compact)
    logo = f"""[{theme.primary}]
    ╔══════════════════════════════════════════╗
    ║  [bold]🚀 DeepSeek Code[/] [dim]v{version:<5}[/]             ║
    ║  [dim]Terminal AI Coding Agent[/]              ║
    ╚══════════════════════════════════════════╝[/]"""

    console.print(logo)
    console.print()

    # Compact info line
    console.print(
        f"  [{theme.dim}]📁[/] [bold]{root}[/]  "
        f"[{theme.dim}]│[/]  "
        f"[{theme.dim}]🤖[/] {model}  "
        f"[{theme.dim}]│[/]  "
        f"[{theme.dim}]⚡[/] {mode}"
    )

    console.print(f"\n  [{theme.dim}]Type [bold]/help[/] for commands • Safety checks enabled[/]")
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVAL PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def print_approval_prompt(
    console: Console,
    action: str,
    details: str = "",
    theme: Theme | None = None,
) -> None:
    """Render an approval request panel."""
    theme = theme or get_theme()

    content = f"[bold {theme.warning}]✋ Approval Required[/]\n\n"
    content += f"Action: [bold]{action}[/]\n"
    if details:
        content += f"[{theme.dim}]{details}[/]"

    console.print(Panel(
        content,
        border_style=theme.border_warning,
        box=box.ROUNDED,
        padding=(0, 2),
    ))


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def get_tool_description(name: str, arguments: dict, theme: Theme | None = None) -> str:
    """Get a human-readable description for a tool execution."""
    theme = theme or get_theme()

    descriptions = {
        "read_file": lambda: f"[{theme.tool_read}]📖 Reading[/] {arguments.get('path', 'file')}",
        "write_file": lambda: f"[{theme.tool_write}]💾 Writing[/] {arguments.get('path', 'file')}",
        "list_dir": lambda: f"[{theme.tool_read}]📂 Listing[/] {arguments.get('path') or 'current directory'}",
        "search": lambda: f"[{theme.tool_read}]🔍 Searching[/] for '{arguments.get('pattern', '')}'",
        "run_shell": lambda: f"[{theme.tool_shell}]🐚 Running[/] {_truncate(arguments.get('cmd', ''), 40)}",
        "read_json_chunk": lambda: f"[{theme.tool_read}]📑 Reading chunk[/] from {arguments.get('path')}",
        "write_json_chunk": lambda: f"[{theme.tool_write}]🖊️ Writing chunk[/] to {arguments.get('path')}",
        "delete_file": lambda: f"[{theme.tool_delete}]🗑️ Deleting[/] {arguments.get('path')}",
    }

    return descriptions.get(name, lambda: f"[{theme.dim}]⚙️ {name}[/]")()


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def print_read_panel(
    console: Console,
    path: str,
    content: str,
    is_error: bool = False,
    theme: Theme | None = None,
) -> None:
    """Render a file content panel."""
    theme = theme or get_theme()

    status_color = theme.success if not is_error else theme.error
    icon = "✓" if not is_error else "✗"

    title = f"[{status_color}]{icon}[/]  ReadFile [bold]{escape(path)}[/]"

    # Calculate stats
    line_count = len(content.splitlines())
    size_kb = len(content.encode("utf-8")) / 1024

    # Truncate strictly for display if too long
    if len(content) > 3000:
        preview = content[:3000] + f"\n\n[{theme.dim}]... (truncated for display) ...[/]"
        display_range = f"Read first 3000 chars ({line_count} lines total, {size_kb:.1f}KB)"
    else:
        preview = content
        display_range = f"Read all {line_count} lines ({size_kb:.1f}KB)"

    body = Text()
    body.append(f"{preview}\n\n", style=theme.foreground)
    body.append(f"[{theme.dim}]{display_range} from {escape(path)}[/]", style=theme.dim)

    panel = Panel(
        body,
        title=title,
        title_align="left",
        border_style=theme.border_secondary,
        box=box.ROUNDED,
        expand=True
    )
    console.print(panel)


def print_list_panel(
    console: Console,
    title_text: str,
    output: str,
    is_error: bool = False,
    theme: Theme | None = None,
) -> None:
    """Render a directory listing or glob result panel."""
    theme = theme or get_theme()

    status_color = theme.success if not is_error else theme.error
    icon = "✓" if not is_error else "✗"

    title = f"[{status_color}]{icon}[/]  {title_text}"

    lines = output.strip().splitlines()
    if not lines:
        content = f"[{theme.dim}](empty result)[/]"
        count_str = ""
    elif len(lines) > 30:
        content = "\n".join(lines[:15] + [f"[{theme.dim}]... (truncated) ...[/]"] + lines[-10:])
        count_str = f"({len(lines)} items)"
    else:
        content = "\n".join(lines)
        count_str = f"({len(lines)} items)"

    body = Text()
    body.append(f"{content}\n", style=theme.foreground)
    if count_str:
        body.append(f"[{theme.dim}]{count_str}[/]", style=theme.dim)

    panel = Panel(
        body,
        title=title,
        title_align="left",
        border_style=theme.border_secondary,
        box=box.ROUNDED,
        expand=True
    )
    console.print(panel)
