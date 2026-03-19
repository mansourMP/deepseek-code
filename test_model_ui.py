#!/usr/bin/env python3
"""
Test the new model selection UI
"""

from rich.console import Console
from deepseek_code.ui.commands import CommandContext, cmd_model, cmd_models
from deepseek_code.ui.themes import get_theme
from unittest.mock import Mock

# Create console
console = Console()

# Create mock agent
agent = Mock()
agent.settings = Mock()
agent.settings.model = "deepseek-chat"
agent.messages = []

# Create mock context
ctx = CommandContext(
    console=console,
    agent=agent,
    root="/Users/mansur/project",
    model_name="deepseek-chat",
    api_key="sk-test",
    base_url="https://api.deepseek.com",
    theme=get_theme("deepseek"),
    auto_approve=False,
    tools_enabled=True,
    readonly_mode=False,
    debug=False,
    approve_reads_enabled=False,
    selected_mode="standard",
    delay_ms=0,
)

console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold cyan]         Testing New Model Selection UI                    [/bold cyan]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

console.print("[bold]1. Running /model (no args - shows all models):[/bold]\n")
cmd_model(ctx, "")

console.print("\n[bold]2. Running /models (same as /model):[/bold]\n")
cmd_models(ctx, "")

console.print("\n[bold]3. Selecting model by number: /model 2[/bold]\n")
cmd_model(ctx, "2")

console.print("\n[bold]4. Selecting model by name: /model deepseek-reasoner[/bold]\n")
cmd_model(ctx, "deepseek-reasoner")

console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
console.print("[bold green]✨ This is the new interactive model selection! ✨[/bold green]")
console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
