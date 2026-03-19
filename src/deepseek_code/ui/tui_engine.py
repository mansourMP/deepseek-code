"""
Async TUI bridge for DeepSeek Code.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from .tui import DeepSeekTUI
from ..engine import Engine
from ..agent import DeepSeekAgent
from ..safety import get_git_branch, get_trust_status

class TUIEngine:
    def __init__(self, engine: Engine, theme: Any, root: Path, agent: DeepSeekAgent):
        self.engine = engine
        self.theme = theme
        self.root = root
        self.agent = agent
        self.tui = DeepSeekTUI(theme, root.name, agent.settings.model)
        
        # Link UI and logic
        self.tui.on_submit = self.handle_input
        self.tui.current_branch = get_git_branch(root)
        self.tui.trust_status = get_trust_status(root)

    def handle_input(self, text: str):
        if not text.strip():
            return
            
        # Add to UI log
        self.tui.append_output(f"\n› {text}\n")
        
        # Run turn in background task
        asyncio.create_task(self.run_turn(text))

    async def run_turn(self, user_input: str):
        # Update status
        self.tui.append_output(f"\n[Thinking...]\n")
        
        # We need a custom stream handler to pipe to TUI
        # This part requires making engine.run_turn aware of the TUI output
        # For now, we'll wrap the standard run_turn and capture stdout if needed,
        # but the best way is to pass an output callback.
        
        try:
            # Simple non-blocking call wrapper
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.engine.run_turn, user_input)
            
            # Update token count
            from ..tokens import count_message_tokens
            used = count_message_tokens(self.agent.messages, self.agent.settings.model)
            total = self.agent.settings.max_context_tokens
            self.tui.context_left = int(((total - used) / total) * 100) if total > 0 else 0
            
        except Exception as e:
            self.tui.append_output(f"\nError: {e}\n")

    async def start(self):
        await self.tui.run_async()
