"""
Animations and loading states for DS Code Agent.

Provides smooth, non-blocking visual feedback during AI thinking,
tool execution, and other long-running operations.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.status import Status
from rich.text import Text

from .themes import Theme, get_theme

# ═══════════════════════════════════════════════════════════════════════════════
# THINKING MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

THINKING_MESSAGES = [
    "Thinking...",
    "Analyzing...",
    "Processing...",
    "Reasoning...",
    "Working...",
]

DEEP_THINKING_MESSAGES = [
    "Deep thinking...",
    "Considering approaches...",
    "Evaluating options...",
    "Planning solution...",
    "Synthesizing...",
]


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS ROTATOR
# ═══════════════════════════════════════════════════════════════════════════════

class StatusRotator:
    """
    Rotates through status messages during long-running operations.
    
    Features:
    - Non-blocking background thread
    - Smooth message transitions
    - Themed styling
    - Clean start/stop semantics
    """

    def __init__(
        self,
        status: Status,
        messages: List[str] | None = None,
        interval: float = 0.8,
        theme: Theme | None = None,
    ):
        self.status = status
        self.messages = messages or THINKING_MESSAGES
        self.interval = interval
        self.theme = theme or get_theme()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> StatusRotator:
        """Start rotating status messages in background."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        """Stop the rotator and wait for thread to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)

    def _run(self) -> None:
        """Background thread that rotates messages."""
        message_cycle = itertools.cycle(self.messages)

        while not self._stop_event.is_set():
            message = next(message_cycle)
            styled_text = Text(message, style=self.theme.primary)
            self.status.update(styled_text)

            # Sleep in small increments so we can respond to stop quickly
            for _ in range(int(self.interval * 10)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

    def __enter__(self) -> StatusRotator:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# THINKING INDICATOR
# ═══════════════════════════════════════════════════════════════════════════════

def show_thinking(
    console: Console,
    deep: bool = False,
    theme: Theme | None = None,
) -> tuple[Status, StatusRotator]:
    """
    Create and start a thinking indicator.
    
    Returns the Status and StatusRotator for manual control.
    
    Usage:
        status, rotator = show_thinking(console)
        try:
            # do work
        finally:
            rotator.stop()
            status.stop()
    """
    theme = theme or get_theme()
    messages = DEEP_THINKING_MESSAGES if deep else THINKING_MESSAGES

    status = Status(
        Text(messages[0], style=theme.primary),
        spinner="dots",
        spinner_style=theme.primary,
    )
    status.start()

    rotator = StatusRotator(status, messages=messages, theme=theme)
    rotator.start()

    return status, rotator


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS INDICATORS
# ═══════════════════════════════════════════════════════════════════════════════

class ToolExecutionSpinner:
    """
    Spinner for tool execution with tool-specific styling.
    """

    def __init__(
        self,
        console: Console,
        tool_name: str,
        description: str,
        theme: Theme | None = None,
    ):
        self.console = console
        self.tool_name = tool_name
        self.description = description
        self.theme = theme or get_theme()
        self._status: Optional[Status] = None

    def __enter__(self) -> ToolExecutionSpinner:
        style = self.theme.get_tool_style(self.tool_name)
        self._status = Status(
            Text(self.description, style=style),
            spinner="dots",
            spinner_style=style,
        )
        self._status.start()
        return self

    def __exit__(self, *args) -> None:
        if self._status:
            self._status.stop()

    def update(self, message: str) -> None:
        """Update the spinner message."""
        if self._status:
            style = self.theme.get_tool_style(self.tool_name)
            self._status.update(Text(message, style=style))


# ═══════════════════════════════════════════════════════════════════════════════
# PULSE ANIMATION
# ═══════════════════════════════════════════════════════════════════════════════

class PulseText:
    """
    Text that pulses between two colors.
    
    Useful for drawing attention to important status changes.
    """

    def __init__(
        self,
        console: Console,
        text: str,
        color1: str,
        color2: str,
        interval: float = 0.5,
    ):
        self.console = console
        self.text = text
        self.color1 = color1
        self.color2 = color2
        self.interval = interval
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None

    def start(self) -> PulseText:
        """Start pulsing in background."""
        self._stop_event.clear()
        self._live = Live(
            Text(self.text, style=self.color1),
            console=self.console,
            refresh_per_second=4,
        )
        self._live.start()

        def pulse():
            colors = itertools.cycle([self.color1, self.color2])
            while not self._stop_event.is_set():
                color = next(colors)
                if self._live:
                    self._live.update(Text(self.text, style=color))
                time.sleep(self.interval)

        threading.Thread(target=pulse, daemon=True).start()
        return self

    def stop(self) -> None:
        """Stop pulsing."""
        self._stop_event.set()
        if self._live:
            self._live.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TYPING EFFECT
# ═══════════════════════════════════════════════════════════════════════════════

def print_typing(
    console: Console,
    text: str,
    delay: float = 0.02,
    style: str = "",
) -> None:
    """
    Print text with a typewriter effect.
    
    Args:
        console: Rich console
        text: Text to print
        delay: Delay between characters in seconds
        style: Rich style string
    """
    if delay <= 0:
        console.print(text, style=style)
        return

    with Live(console=console, auto_refresh=False) as live:
        displayed = ""
        for char in text:
            displayed += char
            live.update(Text(displayed, style=style))
            live.refresh()
            time.sleep(delay)
        console.print()  # Final newline


# ═══════════════════════════════════════════════════════════════════════════════
# SUCCESS/ERROR ANIMATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def show_success(
    console: Console,
    message: str = "Done!",
    theme: Theme | None = None,
) -> None:
    """Show a success indicator."""
    theme = theme or get_theme()
    console.print(f"[{theme.success}]✓[/] {message}")


def show_error(
    console: Console,
    message: str,
    theme: Theme | None = None,
) -> None:
    """Show an error indicator."""
    theme = theme or get_theme()
    console.print(f"[{theme.error}]✗[/] {message}")


def show_warning(
    console: Console,
    message: str,
    theme: Theme | None = None,
) -> None:
    """Show a warning indicator."""
    theme = theme or get_theme()
    console.print(f"[{theme.warning}]⚠[/] {message}")


def show_info(
    console: Console,
    message: str,
    theme: Theme | None = None,
) -> None:
    """Show an info indicator."""
    theme = theme or get_theme()
    console.print(f"[{theme.info}]ℹ[/] {message}")
