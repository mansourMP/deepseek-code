"""
Terminal interface for DeepSeek Code.
Provides a rich interactive CLI with themes, commands, and tool execution.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError, Validator
from rich.console import Console

from . import __version__
from .agent import AgentSettings, DeepSeekAgent
from .config import Config
from .engine import Engine
from .logging_utils import ConversationLogger
from .safety import (
    effective_denylist,
    find_project_root,
    get_git_branch,
    get_trust_status,
)
from .ui.commands import CommandContext, CommandResult, dispatch_command
from .ui.panels import print_status_panel, print_welcome_banner
from .ui.themes import get_theme, set_theme


class CommandCompleter(Completer):
    """Auto-completion for slash commands."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.strip()
        if not text.startswith("/"):
            return
            
        from .ui.commands import COMMANDS
        for name, desc in COMMANDS.items():
            if name.startswith(text):
                yield Completion(name, start_position=-len(text), display=f"{name}  {desc}")


class NonEmptyValidator(Validator):
    """Prevent empty inputs."""

    def validate(self, document) -> None:
        if not document.text.strip():
            raise ValidationError(message="", cursor_position=0)


def _handle_interrupts(interrupted_event: threading.Event, console: Console):
    """Handle Ctrl+C interrupts."""
    def signal_handler(sig, frame):
        if not interrupted_event.is_set():
            interrupted_event.set()
            console.print("\n[yellow]⚠ Interrupted (Ctrl+C)[/]")
        else:
            console.print("\n[red]Force quitting...[/]")
            sys.exit(130)
            
    signal.signal(signal.SIGINT, signal_handler)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--model", help="Override model (default: DEEPSEEK_MODEL or deepseek-chat)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--log", "log_to_file", is_flag=True, help="Write conversation log")
@click.option("--auto-approve", is_flag=True, help="Auto-approve file writes and shell commands")
@click.option("--mode", type=click.Choice(["safe", "standard", "agent", "readonly", "plan"], case_sensitive=False), help="Operating mode")
@click.option("--approve-reads", is_flag=True, help="Require approval for reads/list/search")
@click.version_option(__version__)
def main(
    model: str | None,
    debug: bool,
    log_to_file: bool,
    auto_approve: bool,
    mode: str | None,
    approve_reads: bool,
) -> None:
    """DeepSeek Code - Intelligent Terminal Agent."""
    console = Console(force_terminal=True)
    interrupted = threading.Event()
    _handle_interrupts(interrupted, console)

    # Project setup
    root = find_project_root(Path.cwd())
    load_dotenv(root / ".env")
    
    config = Config.load(root)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        console.print("[red]Error: DEEPSEEK_API_KEY environment variable not set.[/]")
        console.print("[dim]Visit https://platform.deepseek.com to get one.[/]")
        sys.exit(1)

    # Initialize components
    model_name = model or os.getenv("DEEPSEEK_MODEL", config.default_model)
    theme = get_theme(config.theme)
    logger = ConversationLogger(root / ".deepseek-code.log") if log_to_file else None
    
    agent_settings = AgentSettings(
        api_key=api_key,
        model=model_name,
        max_messages=config.max_messages,
        max_context_tokens=config.max_context_tokens,
        debug=debug,
        logger=logger,
        system_prompt=config.get_system_prompt(),
    )
    agent = DeepSeekAgent(agent_settings, console, cwd=str(root))
    
    engine = Engine(
        agent=agent,
        console=console,
        root=root,
        denylist=effective_denylist(config.denylist),
        theme=theme
    )
    
    # Configure engine state from CLI/Config
    selected_mode = (mode or config.mode).lower()
    engine.session_state["auto_approve"] = auto_approve or (selected_mode == "agent")
    engine.approve_reads = approve_reads or config.approve_reads
    engine.readonly = (selected_mode == "readonly")
    
    # UI: Welcome Banner
    print_welcome_banner(console, root, model_name, selected_mode, __version__, theme)
    
    # Session setup
    session = PromptSession(
        completer=CommandCompleter(),
        complete_while_typing=True,
        history=InMemoryHistory(),
        validator=NonEmptyValidator(),
        validate_while_typing=False,
        style=Style.from_dict({
            "prompt": f"fg:{theme.primary}",
            "": f"fg:{theme.foreground}",
            "bottom-toolbar": f"bg:{theme.border_secondary} fg:{theme.foreground}",
            "bottom-toolbar.text": f"fg:{theme.dim}",
            "bottom-toolbar.info": f"fg:{theme.primary} bold",
        }),
    )

    def _get_toolbar():
        from .tokens import count_message_tokens
        used = count_message_tokens(agent.messages, agent.settings.model)
        total = agent.settings.max_context_tokens
        percent = int(((total - used) / total) * 100) if total > 0 else 0
        
        branch = get_git_branch(root)
        trust = get_trust_status(root)
        trust_color = "ansigreen" if trust == "trusted" else "ansiyellow"
        
        return HTML(
            f" 📁 <b>{root.name}</b> <ansicyan>│</ansicyan> "
            f" {branch} <ansicyan>│</ansicyan> "
            f"<{trust_color}>{trust}</ansigreen> <ansicyan>│</ansicyan> "
            f"<ansicyan><b>{agent.settings.model}</b></ansicyan> <ansicyan>│</ansicyan> "
            f"{percent}% context left"
        )

    # Main Interaction Loop
    while True:
        try:
            interrupted.clear()
            
            user_input = session.prompt(
                ANSI(f"\x1b[38;2;{theme.primary.lstrip('#')}m❯\x1b[0m "),
                bottom_toolbar=_get_toolbar,
                refresh_interval=1.0,
            ).strip()
            
            if not user_input:
                continue

            # Handle Commands
            if user_input.startswith("/"):
                ctx = CommandContext(
                    console=console,
                    agent=agent,
                    root=root,
                    model_name=agent.settings.model,
                    api_key=api_key,
                    base_url=agent_settings.base_url,
                    theme=theme,
                    auto_approve=engine.session_state["auto_approve"],
                    tools_enabled=True,
                    readonly_mode=engine.readonly,
                    debug=debug,
                    approve_reads_enabled=engine.approve_reads,
                    selected_mode=selected_mode,
                    delay_ms=config.stream_word_delay_ms,
                )
                
                result = dispatch_command(ctx, user_input)
                
                if result.should_exit:
                    break
                    
                if result.message:
                    if result.message.startswith("mode:"):
                        new_mode = result.message.split(":")[1]
                        selected_mode = new_mode
                        engine.session_state["auto_approve"] = (new_mode == "agent")
                        engine.readonly = (new_mode == "readonly")
                    elif result.message.startswith("approve:"):
                        engine.session_state["auto_approve"] = (result.message.split(":")[1] == "on")
                    elif result.message.startswith("theme:"):
                        theme = get_theme(result.message.split(":")[1])
                        engine.theme = theme
                        session.style = Style.from_dict({
                            "prompt": f"fg:{theme.primary}",
                            "": f"fg:{theme.foreground}",
                            "bottom-toolbar": f"bg:{theme.border_secondary} fg:{theme.foreground}",
                        })
                        
                continue

            # Handle Model Interaction
            engine.run_turn(user_input, plan_mode=(selected_mode == "plan"), stop_event=interrupted)
            
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n[{theme.dim}]Goodbye! 👋[/]")
            break
        except Exception as e:
            console.print(f"[{theme.error}]Error: {e}[/]")
            if debug:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()
