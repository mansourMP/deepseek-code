"""
Interactive model selector for DeepSeek Code.

Provides a beautiful modal dialog for selecting models,
similar to Gemini CLI's interface.
"""

from __future__ import annotations

from typing import List, Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console


class ModelSelector:
    """Interactive model selector with keyboard navigation."""

    def __init__(self, models: List[str], current_model: str, theme_colors: dict):
        self.models = models
        self.current_model = current_model
        self.selected_index = self._get_current_index()
        self.theme = theme_colors
        self.result: Optional[str] = None

    def _get_current_index(self) -> int:
        """Get index of current model."""
        try:
            return self.models.index(self.current_model)
        except ValueError:
            return 0

    def _create_content(self) -> FormattedText:
        """Create the formatted text for the modal."""
        lines = []

        # Title
        lines.append(("", "\n"))
        lines.append(("bold", "  Select Model"))
        lines.append(("", "\n\n"))

        # Model list
        for idx, model in enumerate(self.models):
            is_selected = idx == self.selected_index
            is_current = model == self.current_model

            # Prefix
            if is_selected:
                prefix = "  ❯ "
                style = "bold cyan"
            else:
                prefix = "    "
                style = ""

            # Current indicator
            if is_current:
                indicator = "● "
                indicator_style = "green"
            else:
                indicator = "  "
                indicator_style = ""

            # Model number and name
            lines.append((style, f"{prefix}"))
            lines.append((indicator_style, indicator))
            lines.append((style, f"{idx + 1}. {model}"))
            lines.append(("", "\n"))

        # Instructions
        lines.append(("", "\n"))
        lines.append(("dim", "  ↑/↓: Navigate  Enter: Select  Esc: Cancel"))
        lines.append(("", "\n\n"))

        return FormattedText(lines)

    def _create_layout(self) -> Layout:
        """Create the layout for the modal."""
        content_control = FormattedTextControl(
            text=self._create_content,
            focusable=True,
        )

        content_window = Window(
            content=content_control,
            wrap_lines=True,
        )

        return Layout(HSplit([content_window]))

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for navigation."""
        kb = KeyBindings()

        @kb.add("up")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        def move_down(event):
            if self.selected_index < len(self.models) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select(event):
            self.result = self.models[self.selected_index]
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        def cancel(event):
            self.result = None
            event.app.exit()

        # Number keys for quick selection
        for i in range(1, 10):
            @kb.add(str(i))
            def select_number(event, num=i):
                if num <= len(self.models):
                    self.result = self.models[num - 1]
                    event.app.exit()

        return kb

    def show(self) -> Optional[str]:
        """Show the modal and return selected model (or None if cancelled)."""
        app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_key_bindings(),
            full_screen=False,
            mouse_support=True,
        )

        app.run()
        return self.result


def select_model_interactive(
    models: List[str],
    current_model: str,
    console: Console,
    theme_colors: Optional[dict] = None,
) -> Optional[str]:
    """
    Show interactive model selector.
    
    Args:
        models: List of available model names
        current_model: Currently active model
        console: Rich console for display
        theme_colors: Optional theme color configuration
    
    Returns:
        Selected model name, or None if cancelled
    """
    if not models:
        console.print("[yellow]No models available[/]")
        return None

    theme = theme_colors or {
        "primary": "cyan",
        "success": "green",
        "dim": "dim",
    }

    try:
        selector = ModelSelector(models, current_model, theme)
        return selector.show()
    except Exception as e:
        # Fallback to simple selection if interactive fails
        console.print(f"[yellow]Interactive mode failed: {e}[/]")
        console.print("[dim]Falling back to table view...[/]")
        return None
