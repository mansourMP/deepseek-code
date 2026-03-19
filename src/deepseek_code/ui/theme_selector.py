"""
Interactive theme selector for DeepSeek Code.

Provides a beautiful modal for selecting themes with live preview,
similar to Claude Code's interface.
"""

from __future__ import annotations

from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console

from .themes import THEMES


class ThemeSelector:
    """Interactive theme selector with keyboard navigation."""

    def __init__(self, current_theme: str):
        self.current_theme = current_theme
        self.themes = list(THEMES.keys())
        self.selected_index = self.themes.index(current_theme) if current_theme in self.themes else 0
        self.result: Optional[str] = None

    def _create_content(self) -> FormattedText:
        """Create the formatted text for the selection menu."""
        lines = []

        # Title
        lines.append(("", "\n"))
        lines.append(("bold", "  Choose the text style that looks best with your terminal\n"))
        lines.append(("dim", "  To change this later, run /theme\n\n"))

        # Theme list
        for idx, theme_key in enumerate(self.themes):
            theme = THEMES[theme_key]
            is_selected = idx == self.selected_index
            is_current = theme_key == self.current_theme

            # Prefix
            if is_selected:
                prefix = " ❯ "
                style = "bold cyan"
            else:
                prefix = "   "
                style = ""

            # Number and name
            lines.append((style, f"{prefix}{idx + 1}. {theme.name}"))

            # Current indicator
            if is_current:
                lines.append(("green", " ✔"))

            lines.append(("", "\n"))

        # Instructions
        lines.append(("", "\n"))
        lines.append(("dim", "  ↑/↓: Navigate  Enter: Select  Esc: Cancel"))
        lines.append(("", "\n\n"))

        return FormattedText(lines)

    def _create_preview(self) -> FormattedText:
        """Create a preview of the selected theme."""
        theme_key = self.themes[self.selected_index]
        theme = THEMES[theme_key]

        # Create a preview snippet
        code = """
def greet(name: str):
    print(f"Hello, {name}!")
    return True
"""
        # Note: We can't easily return a Rich object here because prompt_toolkit
        # expects FormattedText. We'll simulate a simple preview or try to use
        # ANSI output if possible, but for now let's show theme colors textually.

        lines = []
        lines.append(("bold", f"\n  Preview: {theme.name}\n"))
        lines.append(("", "  " + "─" * 40 + "\n"))

        # Simulate syntax highlighting roughly using the theme colors
        # This is an approximation since prompt_toolkit styles != Rich styles

        lines.append(("", "\n  "))
        lines.append((f"fg:{theme.primary}", "def"))
        lines.append(("", " "))
        lines.append((f"fg:{theme.secondary}", "greet"))
        lines.append(("", "("))
        lines.append(("", "name"))
        lines.append(("", ": "))
        lines.append((f"fg:{theme.primary}", "str"))
        lines.append(("", "):\n"))

        lines.append(("", "      "))
        lines.append((f"fg:{theme.secondary}", "print"))
        lines.append(("", "("))
        lines.append((f"fg:{theme.success}", 'f"Hello, {name}!"'))
        lines.append(("", ")\n"))

        lines.append(("", "      "))
        lines.append((f"fg:{theme.primary}", "return"))
        lines.append(("", " "))
        lines.append((f"fg:{theme.secondary}", "True"))
        lines.append(("", "\n\n"))

        lines.append(("", "  " + "─" * 40 + "\n"))
        lines.append(("", "\n"))

        return FormattedText(lines)

    def _create_layout(self) -> Layout:
        """Create the layout for the modal."""
        menu_control = FormattedTextControl(
            text=self._create_content,
            focusable=True,
        )

        preview_control = FormattedTextControl(
            text=self._create_preview,
            focusable=False,
        )

        # Split layout: Menu on left, Preview on right (or top/bottom)
        # Let's do top/bottom for simplicity in terminal

        return Layout(HSplit([
            Window(content=menu_control, height=15),
            Window(height=1, char="─", style="class:line"),
            Window(content=preview_control, height=10),
        ]))

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for navigation."""
        kb = KeyBindings()

        @kb.add("up")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        def move_down(event):
            if self.selected_index < len(self.themes) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select(event):
            self.result = self.themes[self.selected_index]
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        def cancel(event):
            self.result = None
            event.app.exit()

        return kb

    def show(self) -> Optional[str]:
        """Show the modal and return selected theme (or None if cancelled)."""
        app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_key_bindings(),
            full_screen=False,
            mouse_support=True,
        )

        app.run()
        return self.result


def select_theme_interactive(
    current_theme: str,
    console: Console,
) -> Optional[str]:
    """
    Show interactive theme selector.
    
    Args:
        current_theme: Currently active theme key
        console: Rich console for display
    
    Returns:
        Selected theme key, or None if cancelled
    """
    try:
        selector = ThemeSelector(current_theme)
        return selector.show()
    except Exception as e:
        console.print(f"[yellow]Interactive mode failed: {e}[/]")
        return None
