"""
Advanced TUI layout for DS Code Agent.
Provides a pinned bottom prompt and status bar with a scrolling conversation area.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea, SearchToolbar
from prompt_toolkit.formatted_text import HTML, ANSI
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.control import Control

class DeepSeekTUI:
    def __init__(self, theme: Any, root_name: str, model_name: str):
        self.theme = theme
        self.root_name = root_name
        self.model_name = model_name
        self.output_text = ""
        self.current_branch = "main"
        self.trust_status = "trusted"
        self.context_left = 100
        
        # Key bindings
        self.kb = KeyBindings()
        
        @self.kb.add("c-c")
        def _(event):
            event.app.exit()

        @self.kb.add("enter")
        def _(event):
            self.on_submit(self.input_field.text)
            self.input_field.text = ""

        # UI Components
        self.output_field = TextArea(
            text="Welcome to DS Code Agent\n(Independent Open Source Project)\n",
            read_only=True,
            scrollbar=True,
        )

        
        self.input_field = TextArea(
            height=1,
            prompt="› ",
            multiline=False,
            wrap_lines=False,
        )

        self.status_bar = Window(
            content=FormattedTextControl(self._get_status_text),
            height=1,
            style=f"bg:{theme.border_secondary} fg:{theme.foreground}",
        )

        # Layout
        self.root_container = HSplit([
            self.output_field,
            Window(height=1, char="─", style=f"fg:{theme.dim}"), # Separator
            self.input_field,
            self.status_bar,
        ])

        self.layout = Layout(self.root_container, focused_element=self.input_field)
        
        self.app: Application = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.5,
        )
        
        self.on_submit: Callable[[str], None] = lambda x: None

    def _get_status_text(self):
        trust_color = "ansigreen" if self.trust_status == "trusted" else "ansiyellow"
        return HTML(
            f"  {self.model_name} <ansicyan>·</ansicyan> "
            f"{self.context_left}% left <ansicyan>·</ansicyan> "
            f" {self.current_branch} <ansicyan>·</ansicyan> "
            f"<{trust_color}>{self.trust_status}</{trust_color}> <ansicyan>·</ansicyan> "
            f"~/{self.root_name}"
        )

    def append_output(self, text: str):
        self.output_text += text
        self.output_field.text = self.output_text
        # Scroll to bottom
        self.output_field.buffer.cursor_position = len(self.output_field.text)

    async def run_async(self):
        await self.app.run_async()
