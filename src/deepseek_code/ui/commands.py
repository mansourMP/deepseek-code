"""
Slash command handlers for DeepSeek Code.

Extracts command logic from the main CLI for better organization
and testability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import httpx
from rich.console import Console
from rich.table import Table

from ..agent import DeepSeekAgent
from ..tokens import count_message_tokens
from ..ui.themes import get_theme, Theme, list_themes, set_theme


@dataclass
class CommandContext:
    """Context passed to command handlers."""
    console: Console
    agent: DeepSeekAgent
    root: Path
    model_name: str
    api_key: str
    base_url: str
    theme: Theme
    
    # Mutable session state
    auto_approve: bool
    tools_enabled: bool
    readonly_mode: bool
    debug: bool
    approve_reads_enabled: bool
    selected_mode: str
    delay_ms: int


@dataclass
class CommandResult:
    """Result of command execution."""
    handled: bool = True
    should_continue: bool = True  # Continue main loop
    should_exit: bool = False
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS: Dict[str, str] = {
    "/help": "Show available commands",
    "/exit": "Exit DeepSeek Code",
    "/clear": "Clear conversation history",
    "/status": "Show session status",
    "/model": "Set model (/model <name>)",
    "/models": "List available models",
    "/tools": "Toggle tools (/tools on|off)",
    "/mode": "Set mode (/mode safe|standard|agent|readonly)",
    "/approve": "Toggle auto-approve (/approve on|off)",
    "/approve-reads": "Toggle read approvals (/approve-reads on|off)",
    "/safe": "Enable safe mode (no tools, no auto-approve)",
    "/readonly": "Enable read-only mode",
    "/history": "Show recent conversation",
    "/debug": "Toggle debug mode (/debug on|off)",
    "/undo": "Undo last file write",
    "/theme": "Set theme (/theme <name>)",
    "/themes": "List available themes",
    "/tokens": "Show token usage",
}


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_help(ctx: CommandContext, args: str) -> CommandResult:
    """Show available commands."""
    theme = ctx.theme
    
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column("Command", style=f"{theme.primary}")
    table.add_column("Description", style=f"{theme.dim}")
    
    for cmd, desc in sorted(COMMANDS.items()):
        table.add_row(cmd, desc)
    
    ctx.console.print(table)
    return CommandResult()


def cmd_exit(ctx: CommandContext, args: str) -> CommandResult:
    """Exit the application."""
    ctx.console.print(f"[{ctx.theme.dim}]Goodbye! 👋[/]")
    return CommandResult(should_exit=True)


def cmd_clear(ctx: CommandContext, args: str) -> CommandResult:
    """Clear conversation history."""
    ctx.agent.reset()
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Conversation cleared")
    return CommandResult()


def cmd_status(ctx: CommandContext, args: str) -> CommandResult:
    """Show session status."""
    from ..ui.panels import print_status_panel
    from .. import __version__
    
    print_status_panel(
        ctx.console,
        root=ctx.root,
        model=ctx.model_name,
        mode=ctx.selected_mode,
        auto_approve=ctx.auto_approve,
        tools_enabled=ctx.tools_enabled,
        readonly_mode=ctx.readonly_mode,
        debug=ctx.debug,
        version=__version__,
        theme=ctx.theme,
    )
    return CommandResult()


def cmd_model(ctx: CommandContext, args: str) -> CommandResult:
    """Set the model or show interactive selector."""
    if not args:
        # Show interactive model selector
        from .model_selector import select_model_interactive
        
        ctx.console.print(f"[{ctx.theme.dim}]Fetching available models...[/]")
        models = _fetch_models(ctx)
        
        if not models:
            ctx.console.print(f"[{ctx.theme.warning}]No models found[/]")
            return CommandResult()
        
        # Show interactive selector
        selected = select_model_interactive(
            models=models,
            current_model=ctx.agent.settings.model,
            console=ctx.console,
            theme_colors={
                "primary": ctx.theme.primary,
                "success": ctx.theme.success,
                "dim": ctx.theme.dim,
            }
        )
        
        if selected:
            ctx.agent.settings.model = selected
            ctx.console.print(
                f"\n[{ctx.theme.success}]✓[/] Model set to "
                f"[bold {ctx.theme.primary}]{selected}[/]"
            )
        else:
            ctx.console.print(f"\n[{ctx.theme.dim}]Selection cancelled[/]")
        
        return CommandResult()
    
    # Check if args is a number (model selection by index)
    if args.isdigit():
        models = _fetch_models(ctx)
        idx = int(args) - 1  # Convert to 0-indexed
        
        if 0 <= idx < len(models):
            selected_model = models[idx]
            ctx.agent.settings.model = selected_model
            ctx.console.print(
                f"[{ctx.theme.success}]✓[/] Model set to "
                f"[bold {ctx.theme.primary}]{selected_model}[/]"
            )
            return CommandResult()
        else:
            ctx.console.print(
                f"[{ctx.theme.error}]Invalid model number:[/] {args}. "
                f"Choose 1-{len(models)}"
            )
            return CommandResult()
    
    # Set the model directly by name
    ctx.agent.settings.model = args
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Model set to [bold]{args}[/]")
    return CommandResult()


def cmd_models(ctx: CommandContext, args: str) -> CommandResult:
    """List available models with selection."""
    return _list_and_select_model(ctx, set_model=True)


def _fetch_models(ctx: CommandContext) -> list[str]:
    """Fetch available models from the API."""
    url = f"{ctx.base_url}/v1/models"
    headers = {"Authorization": f"Bearer {ctx.api_key}"}
    
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        ctx.console.print(f"[{ctx.theme.error}]API Error:[/] {exc}")
        return []
    except httpx.RequestError as exc:
        ctx.console.print(f"[{ctx.theme.error}]Network error:[/] {exc}")
        return []
    
    models = [item.get("id", "") for item in data.get("data", []) if item.get("id")]
    return sorted(models)


def _list_and_select_model(ctx: CommandContext, set_model: bool = False) -> CommandResult:
    """List models and optionally allow selection."""
    from rich.table import Table
    from rich import box
    
    ctx.console.print(f"[{ctx.theme.dim}]Fetching available models...[/]")
    
    models = _fetch_models(ctx)
    
    if not models:
        ctx.console.print(f"[{ctx.theme.warning}]No models found[/]")
        return CommandResult()
    
    # Create a nice table
    table = Table(
        title="[bold]Available Models[/]",
        box=box.ROUNDED,
        border_style=ctx.theme.border_primary,
        show_header=True,
        header_style=f"bold {ctx.theme.primary}",
    )
    table.add_column("#", style=ctx.theme.dim, width=3)
    table.add_column("Model", style="white")
    table.add_column("Status", width=10)
    
    for idx, model in enumerate(models, 1):
        # Use the agent's actual current model, not the context snapshot
        current_model = ctx.agent.settings.model
        is_current = model == current_model
        status = f"[{ctx.theme.success}]● current[/]" if is_current else ""
        
        # Only apply style if it's the current model
        if is_current:
            model_display = f"[bold {ctx.theme.primary}]{model}[/]"
        else:
            model_display = model
        
        table.add_row(str(idx), model_display, status)
    
    ctx.console.print(table)
    ctx.console.print()
    
    # Also use agent's current model for the status message
    current_model = ctx.agent.settings.model
    
    if set_model:
        ctx.console.print(f"[{ctx.theme.dim}]Enter number to select, or model name directly:[/]")
        ctx.console.print(f"[{ctx.theme.dim}]Usage: /model <name> or /model <number>[/]")
    else:
        ctx.console.print(f"[{ctx.theme.dim}]Current model: [{ctx.theme.primary}]{current_model}[/]")
        ctx.console.print(f"[{ctx.theme.dim}]To change: /model <name> or /model <number>[/]")
    
    return CommandResult()


def cmd_tools(ctx: CommandContext, args: str) -> CommandResult:
    """Toggle tools on/off."""
    if args.lower() not in {"on", "off"}:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /tools on|off[/]")
        status = "enabled" if ctx.tools_enabled else "disabled"
        ctx.console.print(f"[{ctx.theme.dim}]Current: {status}[/]")
        return CommandResult()
    
    enabled = args.lower() == "on"
    status = "enabled" if enabled else "disabled"
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Tools {status}")
    
    # Return result with updated state (caller must apply)
    return CommandResult(message=f"tools:{args.lower()}")


def cmd_mode(ctx: CommandContext, args: str) -> CommandResult:
    """Set operating mode."""
    valid_modes = {"safe", "standard", "agent", "readonly"}
    
    if args.lower() not in valid_modes:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /mode safe|standard|agent|readonly[/]")
        ctx.console.print(f"[{ctx.theme.dim}]Current: {ctx.selected_mode}[/]")
        return CommandResult()
    
    mode = args.lower()
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Mode set to [bold]{mode}[/]")
    
    # Describe mode effects
    mode_descriptions = {
        "safe": "No tools, no auto-approve",
        "standard": "Tools enabled, manual approval",
        "agent": "Tools enabled, auto-approve on",
        "readonly": "Read-only tools, no writes",
    }
    ctx.console.print(f"[{ctx.theme.dim}]({mode_descriptions[mode]})[/]")
    
    return CommandResult(message=f"mode:{mode}")


def cmd_approve(ctx: CommandContext, args: str) -> CommandResult:
    """Toggle auto-approve."""
    if args.lower() not in {"on", "off"}:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /approve on|off[/]")
        status = "enabled" if ctx.auto_approve else "disabled"
        ctx.console.print(f"[{ctx.theme.dim}]Current: {status}[/]")
        return CommandResult()
    
    enabled = args.lower() == "on"
    status = "enabled" if enabled else "disabled"
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Auto-approve {status}")
    
    return CommandResult(message=f"approve:{args.lower()}")


def cmd_approve_reads(ctx: CommandContext, args: str) -> CommandResult:
    """Toggle read approval requirement."""
    if args.lower() not in {"on", "off"}:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /approve-reads on|off[/]")
        status = "enabled" if ctx.approve_reads_enabled else "disabled"
        ctx.console.print(f"[{ctx.theme.dim}]Current: {status}[/]")
        return CommandResult()
    
    enabled = args.lower() == "on"
    status = "required" if enabled else "not required"
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Read approvals {status}")
    
    return CommandResult(message=f"approve-reads:{args.lower()}")


def cmd_safe(ctx: CommandContext, args: str) -> CommandResult:
    """Enable safe mode."""
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Safe mode enabled")
    ctx.console.print(f"[{ctx.theme.dim}](tools disabled, auto-approve off)[/]")
    return CommandResult(message="mode:safe")


def cmd_readonly(ctx: CommandContext, args: str) -> CommandResult:
    """Enable read-only mode."""
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Read-only mode enabled")
    ctx.console.print(f"[{ctx.theme.dim}](writes and shell commands blocked)[/]")
    return CommandResult(message="mode:readonly")


def cmd_history(ctx: CommandContext, args: str) -> CommandResult:
    """Show recent conversation history."""
    recent = [
        m for m in ctx.agent.messages 
        if m.get("role") in {"user", "assistant"}
    ][-6:]
    
    if not recent:
        ctx.console.print(f"[{ctx.theme.warning}]No history yet[/]")
        return CommandResult()
    
    for msg in recent:
        role = msg.get("role", "")
        content = (msg.get("content") or "").strip()
        
        if role == "user":
            label = f"[{ctx.theme.primary}]you[/]"
        else:
            label = f"[{ctx.theme.assistant}]assistant[/]"
        
        # Truncate long messages
        if len(content) > 150:
            content = content[:147] + "..."
        
        ctx.console.print(f"{label}: {content}")
    
    return CommandResult()


def cmd_debug(ctx: CommandContext, args: str) -> CommandResult:
    """Toggle debug mode."""
    if args.lower() not in {"on", "off"}:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /debug on|off[/]")
        status = "enabled" if ctx.debug else "disabled"
        ctx.console.print(f"[{ctx.theme.dim}]Current: {status}[/]")
        return CommandResult()
    
    enabled = args.lower() == "on"
    ctx.agent.settings.debug = enabled
    status = "enabled" if enabled else "disabled"
    ctx.console.print(f"[{ctx.theme.success}]✓[/] Debug mode {status}")
    
    return CommandResult(message=f"debug:{args.lower()}")


def cmd_theme(ctx: CommandContext, args: str) -> CommandResult:
    """Set the theme."""
    available = list_themes()
    
    if not args or args.lower() not in available:
        ctx.console.print(f"[{ctx.theme.warning}]Usage: /theme <name>[/]")
        ctx.console.print(f"[{ctx.theme.dim}]Available: {', '.join(available)}[/]")
        ctx.console.print(f"[{ctx.theme.dim}]Current: {ctx.theme.name}[/]")
        return CommandResult()
    
    new_theme = set_theme(args.lower())
    ctx.console.print(f"[{new_theme.success}]✓[/] Theme set to [bold]{new_theme.name}[/]")
    
    return CommandResult(message=f"theme:{args.lower()}")


def cmd_themes(ctx: CommandContext, args: str) -> CommandResult:
    """List available themes."""
    from ..ui.themes import THEMES
    
    ctx.console.print("[bold]Available Themes:[/]")
    for name, theme in THEMES.items():
        marker = " ← current" if name == ctx.theme.name.lower() else ""
        ctx.console.print(
            f"  [{theme.primary}]●[/] [bold]{theme.name}[/]{marker}"
        )
    
    return CommandResult()


def cmd_tokens(ctx: CommandContext, args: str) -> CommandResult:
    """Show token usage."""
    used = count_message_tokens(ctx.agent.messages, ctx.agent.settings.model)
    total = ctx.agent.settings.max_context_tokens
    remaining = max(total - used, 0)
    percent = int((remaining / max(total, 1)) * 100)
    
    # Color based on usage
    if percent > 50:
        color = ctx.theme.success
    elif percent > 20:
        color = ctx.theme.warning
    else:
        color = ctx.theme.error
    
    ctx.console.print(f"[bold]Token Usage:[/]")
    ctx.console.print(f"  Used:      [{color}]{used:,}[/]")
    ctx.console.print(f"  Total:     {total:,}")
    ctx.console.print(f"  Remaining: [{color}]{remaining:,}[/] ({percent}%)")
    
    return CommandResult()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════

COMMAND_HANDLERS: Dict[str, Callable[[CommandContext, str], CommandResult]] = {
    "/help": cmd_help,
    "/exit": cmd_exit,
    "/clear": cmd_clear,
    "/status": cmd_status,
    "/model": cmd_model,
    "/models": cmd_models,
    "/tools": cmd_tools,
    "/mode": cmd_mode,
    "/approve": cmd_approve,
    "/approve-reads": cmd_approve_reads,
    "/safe": cmd_safe,
    "/readonly": cmd_readonly,
    "/history": cmd_history,
    "/debug": cmd_debug,
    "/undo": lambda ctx, args: CommandResult(message="undo"),  # Handled in CLI
    "/theme": cmd_theme,
    "/themes": cmd_themes,
    "/tokens": cmd_tokens,
}


def dispatch_command(ctx: CommandContext, user_input: str) -> CommandResult:
    """
    Parse and dispatch a slash command.
    
    Returns CommandResult indicating how to proceed.
    """
    if not user_input.startswith("/"):
        return CommandResult(handled=False)
    
    # Parse command and args
    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    # Find handler
    handler = COMMAND_HANDLERS.get(command)
    
    if handler:
        return handler(ctx, args)
    
    # Check for partial matches (hints)
    matches = [cmd for cmd in COMMANDS if cmd.startswith(command)]
    
    if matches:
        ctx.console.print(f"[{ctx.theme.dim}]Did you mean: {', '.join(matches)}[/]")
    else:
        ctx.console.print(f"[{ctx.theme.warning}]Unknown command. Type /help for options.[/]")
    
    return CommandResult()


def get_command_completions(prefix: str) -> list[tuple[str, str]]:
    """Get command completions for prompt_toolkit."""
    return [
        (name, desc) 
        for name, desc in COMMANDS.items() 
        if name.startswith(prefix)
    ]
