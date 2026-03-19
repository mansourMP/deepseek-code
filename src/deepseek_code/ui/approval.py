"""
Interactive approval dialog for DeepSeek Code.
Provides a beautiful arrow-key navigation menu for tool approvals.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console
from rich.panel import Panel
from rich import box


class InteractiveMenu:
    """Generic interactive menu with arrow key navigation."""
    
    def __init__(self, title: str, options: List[Dict[str, str]], console: Console):
        self.title = title
        self.options = options
        self.console = console
        self.selected_index = 0
        self.result: Optional[str] = None
        
    def _create_content(self) -> FormattedText:
        lines = []
        
        # Title
        lines.append(("", "\n"))
        lines.append((("bold yellow", f"  ? {self.title}")))
        lines.append(("", "\n\n"))
        
        # Options
        for idx, option in enumerate(self.options):
            is_selected = idx == self.selected_index
            
            if is_selected:
                prefix = "  ❯ "
                style = "bold cyan"
            else:
                prefix = "    "
                style = "white"
                
            label = option["label"]
            desc = option.get("description", "")
            
            lines.append((style, f"{prefix}{label}"))
            if desc and is_selected:
                lines.append((("dim", f"  ({desc})")))
            lines.append(("", "\n"))
            
        lines.append(("", "\n"))
        lines.append((("dim", "  ↑/↓: Navigate  Enter: Select")))
        lines.append(("", "\n"))
        
        return FormattedText(lines)

    def _create_layout(self) -> Layout:
        return Layout(HSplit([
            Window(
                content=FormattedTextControl(
                    text=self._create_content,
                    focusable=True,
                ),
                wrap_lines=True,
            )
        ]))

    def _create_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("up")
        def _(event):
            self.selected_index = max(0, self.selected_index - 1)

        @kb.add("down")
        def _(event):
            self.selected_index = min(len(self.options) - 1, self.selected_index + 1)

        @kb.add("enter")
        def _(event):
            self.result = self.options[self.selected_index]["value"]
            event.app.exit()

        @kb.add("c-c")
        @kb.add("escape")
        def _(event):
            self.result = "deny"  # Default to deny on cancel
            event.app.exit()

        # Shortcut keys (1, 2, 3...)
        for i in range(1, 10):
            @kb.add(str(i))
            def _(event, idx=i-1):
                if idx < len(self.options):
                    self.result = self.options[idx]["value"]
                    event.app.exit()
                    
        return kb

    def show(self) -> str:
        # 1. Capture cursor position before printing anything
        # We can't easily capture exact position without ncurses, 
        # but prompt_toolkit Application runs in an alternate screen or inline.
        # By default application output stays.
        # We can use erase_section logic if we print manually, but app.run() handles IO.
        
        app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_key_bindings(),
            full_screen=False,
            mouse_support=True,
            erase_when_done=True  # <--- THIS IS THE KEY FIX
        )
        app.run()
        return self.result or "deny"


def confirm_action(console: Console, prompt: str, context: str = "") -> str:
    """Show a generic confirmation menu."""
    options = [
        {"label": "Allow", "value": "allow", "description": "Run this time"},
        {"label": "Allow Always", "value": "always", "description": "Allow for this session"},
        {"label": "Deny", "value": "deny", "description": "Skip this action"},
    ]
    
    # Use a rich panel to show context BEFORE the interactive menu
    # because prompt_toolkit takes over the screen area it uses.
    if context:
        console.print(Panel(
            context,
            title="[bold yellow]Approval Context[/]",
            border_style="dim",
            box=box.ROUNDED
        ))

    menu = InteractiveMenu(prompt, options, console)
    return menu.show()

def confirm_write(console: Console, path: str) -> str:
    """Show a specialized menu for file writes."""
    options = [
        {"label": "Allow Write", "value": "allow", "description": "Apply changes"},
        {"label": "Allow Always", "value": "always", "description": "Auto-approve writes"},
        {"label": "View Diff", "value": "diff", "description": "Show changes"},
        {"label": "Edit Manually", "value": "edit", "description": "Open in editor"},
        {"label": "Deny", "value": "deny", "description": "Discard changes"},
    ]
    
    menu = InteractiveMenu(f"Allow modification of {path}?", options, console)
    return menu.show()