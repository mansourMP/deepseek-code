#!/usr/bin/env python3
"""
Visual UI Demo for DeepSeek Code

Run this to see the beautiful UI in action!
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

console = Console()


def demo_welcome():
    """Show welcome banner."""
    console.print()
    welcome = Panel(
        "[bold cyan]DEEPSEEK CODE[/bold cyan]\n\n"
        "Terminal Coding Agent\n"
        "[dim]v0.2.0[/dim]",
        box=box.DOUBLE,
        border_style="cyan",
        padding=(1, 10),
    )
    console.print(welcome)
    console.print()


def demo_status():
    """Show status panel."""
    status_text = """[bold]Session Status[/bold]

Version:     [cyan]0.2.0[/cyan]
Model:       [cyan]deepseek-chat[/cyan]
Mode:        [green]standard[/green]
Directory:   [dim]/Users/user/project[/dim]

Flags:       [green]✓[/green] Tools  [red]✗[/red] Auto-Approve  [red]✗[/red] Read-Only
Context:     [cyan]1,234[/cyan] / [dim]32,000[/dim] tokens ([cyan]4%[/cyan])
Messages:    [cyan]12[/cyan] / [dim]50[/dim]
"""
    
    panel = Panel(
        status_text,
        title="📊 Status",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def demo_model_selection():
    """Show model selection table."""
    table = Table(
        title="[bold]Available Models[/bold]",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Model", style="white")
    table.add_column("Status", width=15)
    
    table.add_row("1", "[bold cyan]deepseek-chat[/bold cyan]", "[green]● current[/green]")
    table.add_row("2", "deepseek-coder", "")
    table.add_row("3", "deepseek-reasoner", "")
    
    console.print(table)
    console.print()
    console.print("[dim]Current model: [cyan]deepseek-chat[/cyan][/dim]")
    console.print("[dim]To change: /model <name> or /model <number>[/dim]")
    console.print()


def demo_diff():
    """Show diff viewer."""
    diff_content = """  12 │ def calculate_total(items: List[Item]) -> float:
  13 │     \"\"\"Calculate total price of items.\"\"\"
  14 │ [red]-   total = 0[/red]
  15 │ [green]+   total = Decimal('0.00')[/green]
  16 │     for item in items:
  17 │ [red]-       total += item.price[/red]
  18 │ [green]+       total += Decimal(str(item.price))[/green]
  19 │     return total
"""
    
    panel = Panel(
        diff_content,
        title="📝 Edit [cyan]src/main.py[/cyan]",
        subtitle="Changes: [green]+2[/green] lines added, [red]-2[/red] lines removed",
        border_style="yellow",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()
    console.print("[green]✓[/green] Approve  [red]✗[/red] Deny  [yellow]✎[/yellow] Edit  [cyan]↻[/cyan] Re-view  [dim][y/n/e/v][/dim]")
    console.print()


def demo_code_syntax():
    """Show syntax highlighted code."""
    code = '''def hello_world():
    """Greet the world."""
    print("Hello, World!")
    return True
'''
    
    syntax = Syntax(
        code,
        "python",
        theme="monokai",
        line_numbers=True,
        background_color="#1e1e1e",
    )
    
    panel = Panel(
        syntax,
        title="🐍 [cyan]example.py[/cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def demo_progress():
    """Show progress indicators."""
    console.print("[bold]Processing...[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task1 = progress.add_task("[cyan]Analyzing codebase...", total=None)
        time.sleep(1)
        progress.update(task1, completed=True)
        
        task2 = progress.add_task("[cyan]Planning modifications...", total=None)
        time.sleep(1)
        progress.update(task2, completed=True)
        
        task3 = progress.add_task("[cyan]Executing changes...", total=None)
        time.sleep(1)
        progress.update(task3, completed=True)
    
    console.print()
    console.print("[green]✨ Success![/green]")
    console.print()


def demo_success():
    """Show success message."""
    success_text = """[green]✓[/green] Created 3 files
[green]✓[/green] Modified 2 files
[green]✓[/green] Tests passing (12/12)

[bold]📊 Summary:[/bold]
   • Lines added: [green]45[/green]
   • Lines removed: [red]12[/red]
   • Files changed: [cyan]5[/cyan]
"""
    
    panel = Panel(
        success_text,
        title="✨ [bold green]Success![/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def demo_error():
    """Show error message."""
    error_text = """Command denied by denylist: [red]rm -rf /[/red]

This command matches the pattern: [yellow]"rm -rf"[/yellow]
Reason: [dim]Destructive file operation[/dim]

[cyan]💡 Tip:[/cyan] Use safer alternatives like 'rm file.txt'
"""
    
    panel = Panel(
        error_text,
        title="❌ [bold red]Error[/bold red]",
        border_style="red",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def demo_themes():
    """Show different themes."""
    themes = [
        ("DeepSeek", "cyan", "#00D9FF (Cyan)", "#B877DB (Purple)"),
        ("Dracula", "magenta", "#BD93F9 (Purple)", "#FF79C6 (Pink)"),
        ("Nord", "blue", "#88C0D0 (Frost)", "#81A1C1 (Blue)"),
        ("Tokyo Night", "bright_blue", "#7AA2F7 (Blue)", "#BB9AF7 (Purple)"),
    ]
    
    for name, color, primary, secondary in themes:
        panel = Panel(
            f"Primary:   {primary}\nSecondary: {secondary}",
            title=f"🎨 [bold]{name} Theme[/bold]",
            border_style=color,
            box=box.ROUNDED,
        )
        console.print(panel)
    
    console.print()


def main():
    """Run the visual demo."""
    console.clear()
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]         DeepSeek Code - Visual UI Demo                    [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
    
    console.print("[bold]1. Welcome Banner[/bold]")
    demo_welcome()
    
    console.print("[bold]2. Status Panel[/bold]")
    demo_status()
    
    console.print("[bold]3. Model Selection Table[/bold]")
    demo_model_selection()
    
    console.print("[bold]4. Diff Viewer[/bold]")
    demo_diff()
    
    console.print("[bold]5. Syntax Highlighted Code[/bold]")
    demo_code_syntax()
    
    console.print("[bold]6. Progress Indicators[/bold]")
    demo_progress()
    
    console.print("[bold]7. Success Message[/bold]")
    demo_success()
    
    console.print("[bold]8. Error Message[/bold]")
    demo_error()
    
    console.print("[bold]9. Theme Showcase[/bold]")
    demo_themes()
    
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold green]✨ This is what DeepSeek Code looks like! ✨[/bold green]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")


if __name__ == "__main__":
    main()
