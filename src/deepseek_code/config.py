"""
Configuration management for DeepSeek Code.

Loads and manages configuration from .deepseek-code.json files
with sensible defaults and validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Config:
    """
    Configuration for DeepSeek Code.
    
    Loaded from .deepseek-code.json in the project root.
    All fields have sensible defaults for immediate use.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # Approval & Safety
    # ─────────────────────────────────────────────────────────────────────────
    approval_mode: str = "prompt"  # "prompt" | "auto"
    auto_approve: bool = False
    approve_reads: bool = False
    readonly: bool = False
    denylist: List[str] = field(default_factory=list)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Model & API
    # ─────────────────────────────────────────────────────────────────────────
    default_model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    max_messages: int = 50
    max_context_tokens: int = 64000
    request_timeout: int = 60
    max_retries: int = 3
    
    # ─────────────────────────────────────────────────────────────────────────
    # Display
    # ─────────────────────────────────────────────────────────────────────────
    stream_word_delay_ms: int = 0
    show_timestamps: bool = False
    show_separator: bool = False  # Changed default: cleaner look
    indent_assistant: bool = True
    assistant_indent: str = "  "
    show_token_usage: bool = True
    show_thinking_time: bool = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # Theme & Appearance
    # ─────────────────────────────────────────────────────────────────────────
    theme: str = "deepseek"
    custom_theme: Optional[Dict[str, str]] = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Behavior
    # ─────────────────────────────────────────────────────────────────────────
    mode: str = "standard"  # "safe" | "standard" | "agent" | "readonly"
    enable_semantic_search: bool = False
    enable_workspace_memory: bool = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────
    log_path: Path | None = None
    log_level: str = "INFO"
    enable_telemetry: bool = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # System Prompts & Context
    # ─────────────────────────────────────────────────────────────────────────
    system_prompt: Optional[str] = None  # Custom system prompt
    system_prompt_file: Optional[str] = None  # Path to system prompt file
    append_system_prompt: Optional[str] = None  # Additional instructions
    load_context_files: bool = True  # Load DEEPSEEK.md files
    
    # ─────────────────────────────────────────────────────────────────────────
    # Advanced
    # ─────────────────────────────────────────────────────────────────────────
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB
    shell_timeout: int = 120  # Increased to 2 minutes
    backup_count: int = 10

    @classmethod
    def load(cls, root: Path) -> "Config":
        """
        Load configuration from .deepseek-code.json.
        
        Falls back to defaults if file doesn't exist or is invalid.
        """
        config_path = root / ".deepseek-code.json"
        
        if not config_path.exists():
            return cls()
        
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        
        return cls(
            # Approval & Safety
            approval_mode=str(data.get("approval_mode", "prompt")),
            auto_approve=bool(data.get("auto_approve", False)),
            approve_reads=bool(data.get("approve_reads", False)),
            readonly=bool(data.get("readonly", False)),
            denylist=list(data.get("denylist", [])),
            
            # Model & API
            default_model=str(data.get("default_model", data.get("model", "deepseek-chat"))),
            base_url=str(data.get("base_url", "https://api.deepseek.com")),
            max_messages=int(data.get("max_messages", 50)),
            max_context_tokens=int(data.get("max_context_tokens", 64000)),
            request_timeout=int(data.get("request_timeout", 60)),
            max_retries=int(data.get("max_retries", 3)),
            
            # Display
            stream_word_delay_ms=int(data.get("stream_word_delay_ms", 0)),
            show_timestamps=bool(data.get("show_timestamps", False)),
            show_separator=bool(data.get("show_separator", False)),
            indent_assistant=bool(data.get("indent_assistant", True)),
            assistant_indent=str(data.get("assistant_indent", "  ")),
            show_token_usage=bool(data.get("show_token_usage", True)),
            show_thinking_time=bool(data.get("show_thinking_time", False)),
            
            # Theme
            theme=str(data.get("theme", "deepseek")),
            custom_theme=data.get("custom_theme"),
            
            # Behavior
            mode=str(data.get("mode", "standard")),
            enable_semantic_search=bool(data.get("enable_semantic_search", False)),
            enable_workspace_memory=bool(data.get("enable_workspace_memory", False)),
            
            # Logging
            log_level=str(data.get("log_level", "INFO")),
            enable_telemetry=bool(data.get("enable_telemetry", False)),
            
            # Advanced
            max_file_size_bytes=int(data.get("max_file_size_bytes", 10 * 1024 * 1024)),
            shell_timeout=int(data.get("shell_timeout", 30)),
            backup_count=int(data.get("backup_count", 10)),
            
            # System Prompts
            system_prompt=data.get("system_prompt"),
            system_prompt_file=data.get("system_prompt_file"),
            append_system_prompt=data.get("append_system_prompt"),
            load_context_files=bool(data.get("load_context_files", True)),
        )

    def save(self, root: Path) -> None:
        """Save configuration to .deepseek-code.json."""
        config_path = root / ".deepseek-code.json"
        config_path.write_text(
            json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def as_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            # Approval & Safety
            "approval_mode": self.approval_mode,
            "auto_approve": self.auto_approve,
            "approve_reads": self.approve_reads,
            "readonly": self.readonly,
            "denylist": self.denylist,
            
            # Model & API
            "default_model": self.default_model,
            "base_url": self.base_url,
            "max_messages": self.max_messages,
            "max_context_tokens": self.max_context_tokens,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            
            # Display
            "stream_word_delay_ms": self.stream_word_delay_ms,
            "show_timestamps": self.show_timestamps,
            "show_separator": self.show_separator,
            "indent_assistant": self.indent_assistant,
            "assistant_indent": self.assistant_indent,
            "show_token_usage": self.show_token_usage,
            "show_thinking_time": self.show_thinking_time,
            
            # Theme
            "theme": self.theme,
            "custom_theme": self.custom_theme,
            
            # Behavior
            "mode": self.mode,
            "enable_semantic_search": self.enable_semantic_search,
            "enable_workspace_memory": self.enable_workspace_memory,
            
            # Logging
            "log_path": str(self.log_path) if self.log_path else None,
            "log_level": self.log_level,
            "enable_telemetry": self.enable_telemetry,
            
            # Advanced
            "max_file_size_bytes": self.max_file_size_bytes,
            "shell_timeout": self.shell_timeout,
            "backup_count": self.backup_count,
            
            # System Prompts
            "system_prompt": self.system_prompt,
            "system_prompt_file": self.system_prompt_file,
            "append_system_prompt": self.append_system_prompt,
            "load_context_files": self.load_context_files,
        }
    
    def get_theme(self) -> "Theme":
        """Get the configured theme, with custom overrides if specified."""
        from .ui.themes import get_theme, create_custom_theme, Theme
        
        base_theme = get_theme(self.theme)
        
        if self.custom_theme:
            return create_custom_theme(
                name=f"{base_theme.name} (custom)",
                base=self.theme,
                **self.custom_theme,
            )
        
        return base_theme
    
    def get_system_prompt(self) -> Optional[str]:
        """
        Get the custom system prompt if configured.
        
        Priority:
        1. Direct system_prompt string
        2. system_prompt_file contents
        3. None (use default)
        """
        if self.system_prompt:
            return self.system_prompt
        
        if self.system_prompt_file:
            try:
                prompt_path = Path(self.system_prompt_file).expanduser()
                return prompt_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                return None
        
        return None
    
    @classmethod
    def load_hierarchical(cls, root: Path) -> "Config":
        """
        Load configuration hierarchically from multiple sources.
        
        Priority (later overrides earlier):
        1. Global: ~/.deepseek/settings.json
        2. Project: {root}/.deepseek-code.json
        3. Local: {root}/.deepseek-code.local.json
        
        Returns:
            Merged configuration
        """
        # Start with defaults
        merged_data: Dict[str, Any] = {}
        
        # 1. Load global config
        global_config = Path.home() / ".deepseek" / "settings.json"
        if global_config.exists():
            try:
                global_data = json.loads(global_config.read_text(encoding="utf-8"))
                merged_data.update(global_data)
            except (json.JSONDecodeError, OSError):
                pass
        
        # 2. Load project config
        project_config = root / ".deepseek-code.json"
        if project_config.exists():
            try:
                project_data = json.loads(project_config.read_text(encoding="utf-8"))
                merged_data.update(project_data)
            except (json.JSONDecodeError, OSError):
                pass
        
        # 3. Load local config (gitignored, for personal overrides)
        local_config = root / ".deepseek-code.local.json"
        if local_config.exists():
            try:
                local_data = json.loads(local_config.read_text(encoding="utf-8"))
                merged_data.update(local_data)
            except (json.JSONDecodeError, OSError):
                pass
        
        # If no config found, return defaults
        if not merged_data:
            return cls()
        
        # Build config from merged data
        return cls(
            # Approval & Safety
            approval_mode=str(merged_data.get("approval_mode", "prompt")),
            auto_approve=bool(merged_data.get("auto_approve", False)),
            approve_reads=bool(merged_data.get("approve_reads", False)),
            readonly=bool(merged_data.get("readonly", False)),
            denylist=list(merged_data.get("denylist", [])),
            
            # Model & API
            default_model=str(merged_data.get("default_model", merged_data.get("model", "deepseek-chat"))),
            base_url=str(merged_data.get("base_url", "https://api.deepseek.com")),
            max_messages=int(merged_data.get("max_messages", 50)),
            max_context_tokens=int(merged_data.get("max_context_tokens", 64000)),
            request_timeout=int(merged_data.get("request_timeout", 60)),
            max_retries=int(merged_data.get("max_retries", 3)),
            
            # Display
            stream_word_delay_ms=int(merged_data.get("stream_word_delay_ms", 0)),
            show_timestamps=bool(merged_data.get("show_timestamps", False)),
            show_separator=bool(merged_data.get("show_separator", False)),
            indent_assistant=bool(merged_data.get("indent_assistant", True)),
            assistant_indent=str(merged_data.get("assistant_indent", "  ")),
            show_token_usage=bool(merged_data.get("show_token_usage", True)),
            show_thinking_time=bool(merged_data.get("show_thinking_time", False)),
            
            # Theme
            theme=str(merged_data.get("theme", "deepseek")),
            custom_theme=merged_data.get("custom_theme"),
            
            # Behavior
            mode=str(merged_data.get("mode", "standard")),
            enable_semantic_search=bool(merged_data.get("enable_semantic_search", False)),
            enable_workspace_memory=bool(merged_data.get("enable_workspace_memory", False)),
            
            # Logging
            log_level=str(merged_data.get("log_level", "INFO")),
            enable_telemetry=bool(merged_data.get("enable_telemetry", False)),
            
            # System Prompts
            system_prompt=merged_data.get("system_prompt"),
            system_prompt_file=merged_data.get("system_prompt_file"),
            append_system_prompt=merged_data.get("append_system_prompt"),
            load_context_files=bool(merged_data.get("load_context_files", True)),
            
            # Advanced
            max_file_size_bytes=int(merged_data.get("max_file_size_bytes", 10 * 1024 * 1024)),
            shell_timeout=int(merged_data.get("shell_timeout", 30)),
            backup_count=int(merged_data.get("backup_count", 10)),
        )



# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

EXAMPLE_CONFIG = """{
  "// DeepSeek Code Configuration": "https://github.com/deepseek/deepseek-code",
  
  "// Approval & Safety": "",
  "approval_mode": "prompt",
  "auto_approve": false,
  "approve_reads": false,
  "readonly": false,
  "denylist": ["rm -rf", "sudo", "mkfs"],
  
  "// Model & API": "",
  "default_model": "deepseek-chat",
  "max_messages": 50,
  "max_context_tokens": 64000,
  
  "// Display": "",
  "stream_word_delay_ms": 0,
  "show_token_usage": true,
  
  "// Theme (options: deepseek, github, dracula, nord, monokai, tokyo, catppuccin, light)": "",
  "theme": "deepseek",
  
  "// Behavior (options: safe, standard, agent, readonly)": "",
  "mode": "standard"
}
"""


def create_example_config(root: Path) -> Path:
    """Create an example configuration file."""
    config_path = root / ".deepseek-code.json"
    config_path.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    return config_path

