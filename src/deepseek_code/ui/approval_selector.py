"""
Interactive approval mode selector for DeepSeek Code.

Provides a beautiful modal for selecting approval/mode settings,
similar to Codex's interface.
"""

from __future__ import annotations

from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console


class ApprovalModeSelector:
    """Interactive approval mode selector with keyboard navigation."""
    
    MODES = [
        {
            "name": "Safe (Read Only)",
            "key": "safe",
            "description": "Chat only. No code access. Safest option.",
            "details": "Agent cannot read or modify files. Cannot run commands.",
        },
        {
            "name": "Standard (Manual Approval)",
            "key": "standard",
            "description": "Read and edit files with approval. Recommended.",
            "details": "Requires approval to edit files and run commands.",
        },
        {
            "name": "Plan Mode",
            "key": "plan",
            "description": "Read-only exploration and planning.",
            "details": "Agent can read files and create plans, but cannot make changes.",
        },
        {
            "name": "Agent (Auto-Approve)",
            "key": "agent",
            "description": "Autonomous coding within workspace.",
            "details": "Read and edit files, and run commands automatically.",
        },
        {
            "name": "Read Only",
            "key": "readonly",
            "description": "Read-only access to codebase.",
            "details": "Can read files and search, but cannot modify anything.",
        },
    ]
    
    def __init__(self, current_mode: str):
        self.current_mode = current_mode
        self.selected_index = self._get_current_index()
        self.result: Optional[str] = None
        
    def _get_current_index(self) -> int:
        """Get index of current mode."""
        for idx, mode in enumerate(self.MODES):
            if mode["key"] == self.current_mode:
                return idx
        return 1  # Default to Standard
    
    def _create_content(self) -> FormattedText:
        """Create the formatted text for the modal."""
        lines = []
        
        # Title
        lines.append(("", "\n"))
        lines.append(("bold", "  Select Approval Mode"))
        lines.append(("", "\n\n"))
        
        # Mode list
        for idx, mode in enumerate(self.MODES):
            is_selected = idx == self.selected_index
            is_current = mode["key"] == self.current_mode
            
            # Prefix
            if is_selected:
                prefix = "  › "
                style = "bold cyan"
            else:
                prefix = "    "
                style = ""
            
            # Number and name
            lines.append((style, f"{prefix}{idx + 1}. {mode['name']}"))
            
            # Current indicator
            if is_current:
                lines.append(("green", " (current)"))
            
            lines.append(("", "\n"))
            
            # Description (indented)
            if is_selected:
                lines.append(("dim", f"      {mode['description']}"))
                lines.append(("", "\n"))
                lines.append(("dim", f"      {mode['details']}"))
                lines.append(("", "\n"))
        
        # Instructions
        lines.append(("", "\n"))
        lines.append(("dim", "  ↑/↓: Navigate  Enter: Select  Esc: Cancel  1-5: Quick select"))
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
            if self.selected_index < len(self.MODES) - 1:
                self.selected_index += 1
        
        @kb.add("enter")
        def select(event):
            self.result = self.MODES[self.selected_index]["key"]
            event.app.exit()
        
        @kb.add("escape")
        @kb.add("c-c")
        def cancel(event):
            self.result = None
            event.app.exit()
        
        # Number keys for quick selection
        for i in range(1, 6):
            @kb.add(str(i))
            def select_number(event, num=i):
                if num <= len(self.MODES):
                    self.result = self.MODES[num - 1]["key"]
                    event.app.exit()
        
        return kb
    
    def show(self) -> Optional[str]:
        """Show the modal and return selected mode (or None if cancelled)."""
        app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_key_bindings(),
            full_screen=False,
            mouse_support=True,
        )
        
        app.run()
        return self.result


def select_approval_mode(
    current_mode: str,
    console: Console,
) -> Optional[str]:
    """
    Show interactive approval mode selector.
    
    Args:
        current_mode: Currently active mode
        console: Rich console for display
    
    Returns:
        Selected mode key, or None if cancelled
    """
    try:
        selector = ApprovalModeSelector(current_mode)
        return selector.show()
    except Exception as e:
        # Fallback to simple selection if interactive fails
        console.print(f"[yellow]Interactive mode failed: {e}[/]")
        console.print("[dim]Use /mode <name> instead[/]")
        return None
