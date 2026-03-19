"""
Session management for DS Code Agent.

Handles session state, backups, undo functionality, and persistence.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FileBackup:
    """Record of a file backup for undo functionality."""
    original_path: str
    backup_path: str
    timestamp: float
    content_hash: str = ""


@dataclass
class SessionState:
    """
    Holds all mutable session state.
    
    This centralizes state that was previously scattered across
    multiple variables in the main CLI function.
    """
    # Approval state
    auto_approve: bool = False
    approve_reads: bool = False

    # Mode settings
    tools_enabled: bool = True
    readonly_mode: bool = False
    debug: bool = False
    selected_mode: str = "standard"

    # Model settings
    model_name: str = "deepseek-chat"
    delay_ms: int = 0

    # Backup history for undo
    backups: List[FileBackup] = field(default_factory=list)

    # Theme
    theme_name: str = "deepseek"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dict."""
        return {
            "auto_approve": self.auto_approve,
            "approve_reads": self.approve_reads,
            "tools_enabled": self.tools_enabled,
            "readonly_mode": self.readonly_mode,
            "debug": self.debug,
            "selected_mode": self.selected_mode,
            "model_name": self.model_name,
            "delay_ms": self.delay_ms,
            "theme_name": self.theme_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionState:
        """Deserialize state from dict."""
        return cls(
            auto_approve=data.get("auto_approve", False),
            approve_reads=data.get("approve_reads", False),
            tools_enabled=data.get("tools_enabled", True),
            readonly_mode=data.get("readonly_mode", False),
            debug=data.get("debug", False),
            selected_mode=data.get("selected_mode", "standard"),
            model_name=data.get("model_name", "deepseek-chat"),
            delay_ms=data.get("delay_ms", 0),
            theme_name=data.get("theme_name", "deepseek"),
        )

    def apply_mode(self, mode: str) -> None:
        """Apply mode-specific settings."""
        mode = mode.lower()
        self.selected_mode = mode

        if mode == "safe":
            self.tools_enabled = False
            self.auto_approve = False
            self.readonly_mode = False
        elif mode == "standard":
            self.tools_enabled = True
            self.readonly_mode = False
        elif mode == "agent":
            self.tools_enabled = True
            self.auto_approve = True
            self.readonly_mode = False
        elif mode == "readonly":
            self.tools_enabled = True
            self.readonly_mode = True
            self.auto_approve = False


class BackupManager:
    """
    Manages file backups for undo functionality.
    
    Features:
    - Automatic backup before writes
    - Undo support
    - Cleanup of old backups
    - Backup history persistence
    """

    MAX_BACKUPS_PER_FILE = 10
    MAX_TOTAL_BACKUPS = 100

    def __init__(self, root: Path):
        # Resolve to handle symlinks (e.g., macOS /var -> /private/var)
        self.root = root.resolve()
        self.backup_dir = self.root / ".deepseek-code" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._history: List[FileBackup] = []

    def create_backup(self, path: str, content: str) -> FileBackup:
        """
        Create a backup of file content before modification.
        
        Returns FileBackup object for undo functionality.
        """
        # Resolve the target path relative to our resolved root
        if Path(path).is_absolute():
            target = Path(path).resolve()
        else:
            target = (self.root / path).resolve()
        rel = target.relative_to(self.root)

        # Create backup directory structure
        backup_dir = self.backup_dir / rel.parent
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = time.time()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_name = f"{rel.name}.{stamp}.bak"
        backup_path = backup_dir / backup_name

        # Write backup
        backup_path.write_text(content, encoding="utf-8")

        # Create backup record
        backup = FileBackup(
            original_path=str(target),
            backup_path=str(backup_path),
            timestamp=timestamp,
        )

        # Add to history
        self._history.append(backup)

        # Cleanup old backups
        self._cleanup_backups(rel)

        return backup

    def get_last_backup(self) -> Optional[FileBackup]:
        """Get the most recent backup."""
        return self._history[-1] if self._history else None

    def undo_last(self) -> Optional[str]:
        """
        Undo the last file write.
        
        Returns the path of the restored file, or None if no backup.
        """
        if not self._history:
            return None

        backup = self._history.pop()
        backup_path = Path(backup.backup_path)
        target_path = Path(backup.original_path)

        if not backup_path.exists():
            return None

        # Restore content
        content = backup_path.read_text(encoding="utf-8", errors="replace")
        target_path.write_text(content, encoding="utf-8")

        return backup.original_path

    def _cleanup_backups(self, rel_path: Path) -> None:
        """Remove old backups to prevent disk bloat."""
        backup_dir = self.backup_dir / rel_path.parent

        if not backup_dir.exists():
            return

        # Find all backups for this file
        pattern = f"{rel_path.name}.*.bak"
        backups = sorted(
            backup_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Keep only MAX_BACKUPS_PER_FILE
        for old_backup in backups[self.MAX_BACKUPS_PER_FILE:]:
            try:
                old_backup.unlink()
            except OSError:
                pass

    def clear_history(self) -> int:
        """Clear backup history, return number of backups cleared."""
        count = len(self._history)
        self._history.clear()
        return count


class ChunkStateManager:
    """
    Manages state for chunked JSON processing.
    
    Tracks progress through large JSON files and enables resume.
    """

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path
        self._state: Dict[str, Any] = {}

        if state_path and state_path.exists():
            self._load()

    def _load(self) -> None:
        """Load state from file."""
        try:
            self._state = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            self._state = {}

    def _save(self) -> None:
        """Save state to file."""
        if not self.state_path:
            return

        self.state_path.write_text(
            json.dumps(self._state, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    @property
    def last_index(self) -> int:
        """Get the last processed index."""
        return self._state.get("last_index", 0)

    @last_index.setter
    def last_index(self, value: int) -> None:
        """Set the last processed index."""
        self._state["last_index"] = value
        self._save()

    def update_progress(self, start: int, count: int) -> None:
        """Update progress after processing a chunk."""
        self._state["last_index"] = start + count
        self._state["last_updated"] = time.time()
        self._save()

    def reset(self) -> None:
        """Reset state."""
        self._state = {}
        self._save()


class SessionPersistence:
    """
    Optional session persistence for resuming work.
    
    Saves and loads session state, conversation snippets,
    and workspace context.
    """

    def __init__(self, root: Path):
        self.root = root
        self.session_file = root / ".deepseek-code" / "session.json"

    def save(self, state: SessionState, messages: List[Dict[str, Any]]) -> None:
        """Save session state and recent messages."""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "state": state.to_dict(),
            "messages": messages[-20:],  # Keep last 20 messages
            "saved_at": time.time(),
        }

        self.session_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> tuple[Optional[SessionState], List[Dict[str, Any]]]:
        """Load saved session if exists."""
        if not self.session_file.exists():
            return None, []

        try:
            data = json.loads(self.session_file.read_text(encoding="utf-8"))
            state = SessionState.from_dict(data.get("state", {}))
            messages = data.get("messages", [])
            return state, messages
        except (json.JSONDecodeError, OSError):
            return None, []

    def clear(self) -> None:
        """Clear saved session."""
        if self.session_file.exists():
            self.session_file.unlink()
