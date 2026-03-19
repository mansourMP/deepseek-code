"""
Comprehensive test suite for DeepSeek Code.

Tests cover:
- Safety and sandboxing
- Configuration loading
- Session management
- UI components
- Tool execution
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sandbox_root(tmp_path: Path) -> Path:
    """Create a temporary sandbox directory."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    
    # Create some test files
    (sandbox / "test.py").write_text("print('hello')")
    (sandbox / "subdir").mkdir()
    (sandbox / "subdir" / "nested.txt").write_text("nested content")
    
    return sandbox


@pytest.fixture
def mock_console() -> Mock:
    """Create a mock Rich console."""
    console = Mock()
    console.print = Mock()
    console.size = Mock()
    console.size.width = 80
    return console


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathResolution:
    """Test path resolution and sandboxing."""
    
    def test_resolve_relative_path(self, sandbox_root: Path):
        from deepseek_code.safety import resolve_path
        
        result = resolve_path(sandbox_root, "test.py")
        assert result == sandbox_root / "test.py"
    
    def test_resolve_nested_path(self, sandbox_root: Path):
        from deepseek_code.safety import resolve_path
        
        result = resolve_path(sandbox_root, "subdir/nested.txt")
        assert result == sandbox_root / "subdir" / "nested.txt"
    
    def test_path_traversal_blocked(self, sandbox_root: Path):
        from deepseek_code.safety import resolve_path, PathEscapeError
        
        with pytest.raises(PathEscapeError):
            resolve_path(sandbox_root, "../etc/passwd")
    
    def test_absolute_path_escape_blocked(self, sandbox_root: Path):
        from deepseek_code.safety import resolve_path, PathEscapeError
        
        with pytest.raises(PathEscapeError):
            resolve_path(sandbox_root, "/etc/passwd")
    
    def test_double_dot_escape_blocked(self, sandbox_root: Path):
        from deepseek_code.safety import resolve_path, PathEscapeError
        
        with pytest.raises(PathEscapeError):
            resolve_path(sandbox_root, "subdir/../../etc/passwd")
    
    def test_is_path_safe(self, sandbox_root: Path):
        from deepseek_code.safety import is_path_safe
        
        assert is_path_safe(sandbox_root, "test.py") is True
        assert is_path_safe(sandbox_root, "../etc/passwd") is False


class TestCommandValidation:
    """Test command denylist and validation."""
    
    def test_safe_commands_allowed(self):
        from deepseek_code.safety import is_command_allowed, DEFAULT_DENYLIST
        
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "grep pattern *.py",
            "python script.py",
            "npm install",
            "git status",
        ]
        
        for cmd in safe_commands:
            assert is_command_allowed(cmd, DEFAULT_DENYLIST), f"Should allow: {cmd}"
    
    def test_dangerous_commands_blocked(self):
        from deepseek_code.safety import is_command_allowed, DEFAULT_DENYLIST
        
        dangerous_commands = [
            "rm -rf /",
            "sudo apt install",
            "dd if=/dev/zero",
            "mkfs.ext4 /dev/sda",
            "chmod -R 777 /",
        ]
        
        for cmd in dangerous_commands:
            assert not is_command_allowed(cmd, DEFAULT_DENYLIST), f"Should block: {cmd}"
    
    def test_sanitize_command_blocks_injection(self):
        from deepseek_code.safety import sanitize_command, CommandDeniedError
        
        dangerous_patterns = [
            "echo test; rm -rf /",
            "cat file | sudo tee",
            "echo `whoami`",
            "echo $(id)",
        ]
        
        for cmd in dangerous_patterns:
            with pytest.raises(CommandDeniedError):
                sanitize_command(cmd)
    
    def test_effective_denylist_merges_custom(self):
        from deepseek_code.safety import effective_denylist, DEFAULT_DENYLIST
        
        custom = ["my-dangerous-command", "another-bad-thing"]
        result = effective_denylist(custom)
        
        assert len(result) == len(DEFAULT_DENYLIST) + len(custom)
        assert "my-dangerous-command" in result


class TestSensitiveFiles:
    """Test sensitive file detection."""
    
    def test_detects_env_files(self):
        from deepseek_code.safety import is_sensitive_file
        
        assert is_sensitive_file(Path(".env")) is True
        assert is_sensitive_file(Path(".env.local")) is True
        assert is_sensitive_file(Path(".env.production")) is True
    
    def test_detects_key_files(self):
        from deepseek_code.safety import is_sensitive_file
        
        assert is_sensitive_file(Path("private.key")) is True
        assert is_sensitive_file(Path("server.pem")) is True
        assert is_sensitive_file(Path("id_rsa")) is True
    
    def test_allows_normal_files(self):
        from deepseek_code.safety import is_sensitive_file
        
        assert is_sensitive_file(Path("main.py")) is False
        assert is_sensitive_file(Path("README.md")) is False
        assert is_sensitive_file(Path("config.json")) is False


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfiguration:
    """Test configuration loading and saving."""
    
    def test_default_config(self):
        from deepseek_code.config import Config
        
        config = Config()
        
        assert config.approval_mode == "prompt"
        assert config.auto_approve is False
        assert config.mode == "standard"
        assert config.theme == "deepseek"
        assert config.max_context_tokens == 64000
    
    def test_load_from_file(self, tmp_path: Path):
        from deepseek_code.config import Config
        
        config_data = {
            "theme": "dracula",
            "mode": "agent",
            "auto_approve": True,
            "max_context_tokens": 64000,
        }
        
        config_file = tmp_path / ".deepseek-code.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Config.load(tmp_path)
        
        assert config.theme == "dracula"
        assert config.mode == "agent"
        assert config.auto_approve is True
        assert config.max_context_tokens == 64000
    
    def test_load_missing_file_returns_defaults(self, tmp_path: Path):
        from deepseek_code.config import Config
        
        config = Config.load(tmp_path)
        
        assert config.theme == "deepseek"
        assert config.mode == "standard"
    
    def test_save_config(self, tmp_path: Path):
        from deepseek_code.config import Config
        
        config = Config(theme="nord", mode="safe")
        config.save(tmp_path)
        
        config_file = tmp_path / ".deepseek-code.json"
        assert config_file.exists()
        
        loaded = json.loads(config_file.read_text())
        assert loaded["theme"] == "nord"
        assert loaded["mode"] == "safe"
    
    def test_as_dict_roundtrip(self):
        from deepseek_code.config import Config
        
        config = Config(
            theme="github",
            mode="agent",
            auto_approve=True,
            denylist=["custom-deny"],
        )
        
        config_dict = config.as_dict()
        
        assert config_dict["theme"] == "github"
        assert config_dict["mode"] == "agent"
        assert config_dict["auto_approve"] is True
        assert "custom-deny" in config_dict["denylist"]


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionState:
    """Test session state management."""
    
    def test_default_state(self):
        from deepseek_code.session import SessionState
        
        state = SessionState()
        
        assert state.auto_approve is False
        assert state.tools_enabled is True
        assert state.selected_mode == "standard"
    
    def test_apply_safe_mode(self):
        from deepseek_code.session import SessionState
        
        state = SessionState()
        state.apply_mode("safe")
        
        assert state.selected_mode == "safe"
        assert state.tools_enabled is False
        assert state.auto_approve is False
    
    def test_apply_agent_mode(self):
        from deepseek_code.session import SessionState
        
        state = SessionState()
        state.apply_mode("agent")
        
        assert state.selected_mode == "agent"
        assert state.tools_enabled is True
        assert state.auto_approve is True
    
    def test_apply_readonly_mode(self):
        from deepseek_code.session import SessionState
        
        state = SessionState()
        state.apply_mode("readonly")
        
        assert state.selected_mode == "readonly"
        assert state.tools_enabled is True
        assert state.readonly_mode is True
    
    def test_to_dict_from_dict_roundtrip(self):
        from deepseek_code.session import SessionState
        
        state = SessionState(
            auto_approve=True,
            selected_mode="agent",
            model_name="deepseek-coder",
        )
        
        state_dict = state.to_dict()
        restored = SessionState.from_dict(state_dict)
        
        assert restored.auto_approve == state.auto_approve
        assert restored.selected_mode == state.selected_mode
        assert restored.model_name == state.model_name


class TestBackupManager:
    """Test backup and undo functionality."""
    
    def test_create_backup(self, sandbox_root: Path):
        from deepseek_code.session import BackupManager
        
        manager = BackupManager(sandbox_root)
        
        test_file = sandbox_root / "test.py"
        original_content = test_file.read_text()
        
        backup = manager.create_backup("test.py", original_content)
        
        assert backup.original_path == str(test_file)
        assert Path(backup.backup_path).exists()
    
    def test_undo_restores_content(self, sandbox_root: Path):
        from deepseek_code.session import BackupManager
        
        manager = BackupManager(sandbox_root)
        
        test_file = sandbox_root / "test.py"
        original_content = test_file.read_text()
        
        # Create backup
        manager.create_backup("test.py", original_content)
        
        # Modify file
        test_file.write_text("modified content")
        
        # Undo
        restored_path = manager.undo_last()
        
        assert restored_path == str(test_file)
        assert test_file.read_text() == original_content
    
    def test_get_last_backup(self, sandbox_root: Path):
        from deepseek_code.session import BackupManager
        
        manager = BackupManager(sandbox_root)
        
        assert manager.get_last_backup() is None
        
        test_file = sandbox_root / "test.py"
        manager.create_backup("test.py", test_file.read_text())
        
        assert manager.get_last_backup() is not None


# ═══════════════════════════════════════════════════════════════════════════════
# THEME TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestThemes:
    """Test theme system."""
    
    def test_default_theme(self):
        from deepseek_code.ui.themes import get_theme, THEMES
        
        theme = get_theme()
        assert theme == THEMES["deepseek"]
    
    def test_get_theme_by_name(self):
        from deepseek_code.ui.themes import get_theme
        
        theme = get_theme("dracula")
        assert theme.name == "Dracula"
        
        theme = get_theme("github")
        assert theme.name == "GitHub Dark"
    
    def test_invalid_theme_returns_default(self):
        from deepseek_code.ui.themes import get_theme, THEMES
        
        theme = get_theme("nonexistent")
        assert theme == THEMES["deepseek"]
    
    def test_all_themes_have_required_fields(self):
        from deepseek_code.ui.themes import THEMES
        
        required_fields = [
            "primary", "secondary", "success", "error",
            "warning", "dim", "diff_add", "diff_remove",
        ]
        
        for name, theme in THEMES.items():
            for field in required_fields:
                assert hasattr(theme, field), f"Theme {name} missing {field}"
                assert getattr(theme, field), f"Theme {name} has empty {field}"
    
    def test_create_custom_theme(self):
        from deepseek_code.ui.themes import create_custom_theme
        
        custom = create_custom_theme(
            name="My Theme",
            base="deepseek",
            primary="#FF0000",
        )
        
        assert custom.name == "My Theme"
        assert custom.primary == "#FF0000"
        # Other fields should come from base theme
        assert custom.success  # Not empty


class TestListThemes:
    """Test theme listing."""
    
    def test_list_themes(self):
        from deepseek_code.ui.themes import list_themes
        
        themes = list_themes()
        
        assert "deepseek" in themes
        assert "dracula" in themes
        assert "github" in themes
        assert "nord" in themes


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiffPanel:
    """Test diff functionality."""
    
    def test_diff_preview_detects_changes(self):
        from deepseek_code.ui.panels import diff_preview
        
        before = "line1\nline2\nline3"
        after = "line1\nmodified\nline3"
        
        diff = diff_preview(before, after)
        
        assert len(diff) > 0
        assert any("-line2" in line for line in diff)
        assert any("+modified" in line for line in diff)
    
    def test_diff_preview_no_changes(self):
        from deepseek_code.ui.panels import diff_preview
        
        content = "same content"
        diff = diff_preview(content, content)
        
        assert len(diff) == 0
    
    def test_diff_summary_counts_lines(self):
        from deepseek_code.ui.panels import diff_summary
        
        diff_lines = [
            "--- before",
            "+++ after",
            "@@ -1,3 +1,3 @@",
            " unchanged",
            "-removed1",
            "-removed2",
            "+added1",
        ]
        
        added, removed = diff_summary(diff_lines)
        
        assert added == 1
        assert removed == 2


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommandDispatch:
    """Test slash command dispatching."""
    
    def test_help_command(self, mock_console: Mock, sandbox_root: Path):
        from deepseek_code.ui.commands import dispatch_command, CommandContext
        from deepseek_code.ui.themes import get_theme
        
        ctx = self._make_context(mock_console, sandbox_root)
        result = dispatch_command(ctx, "/help")
        
        assert result.handled is True
        assert result.should_exit is False
        mock_console.print.assert_called()
    
    def test_exit_command(self, mock_console: Mock, sandbox_root: Path):
        ctx = self._make_context(mock_console, sandbox_root)
        from deepseek_code.ui.commands import dispatch_command
        
        result = dispatch_command(ctx, "/exit")
        
        assert result.handled is True
        assert result.should_exit is True
    
    def test_unknown_command(self, mock_console: Mock, sandbox_root: Path):
        ctx = self._make_context(mock_console, sandbox_root)
        from deepseek_code.ui.commands import dispatch_command
        
        result = dispatch_command(ctx, "/unknowncommand")
        
        assert result.handled is True  # Handled by showing error
    
    def test_non_command_not_handled(self, mock_console: Mock, sandbox_root: Path):
        ctx = self._make_context(mock_console, sandbox_root)
        from deepseek_code.ui.commands import dispatch_command
        
        result = dispatch_command(ctx, "regular input")
        
        assert result.handled is False
    
    def _make_context(self, console: Mock, root: Path):
        from deepseek_code.ui.commands import CommandContext
        from deepseek_code.ui.themes import get_theme
        
        agent = Mock()
        agent.messages = []
        agent.settings = Mock()
        agent.settings.model = "test-model"
        agent.settings.max_context_tokens = 32000
        
        return CommandContext(
            console=console,
            agent=agent,
            root=root,
            model_name="test-model",
            api_key="test-key",
            base_url="https://api.test.com",
            theme=get_theme(),
            auto_approve=False,
            tools_enabled=True,
            readonly_mode=False,
            debug=False,
            approve_reads_enabled=False,
            selected_mode="standard",
            delay_ms=0,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_config_to_theme(self, tmp_path: Path):
        """Test loading theme from config file."""
        from deepseek_code.config import Config
        
        config_data = {"theme": "nord"}
        config_file = tmp_path / ".deepseek-code.json"
        config_file.write_text(json.dumps(config_data))
        
        config = Config.load(tmp_path)
        theme = config.get_theme()
        
        assert theme.name == "Nord"
    
    def test_backup_and_single_undo(self, sandbox_root: Path):
        """Test simple backup and undo workflow."""
        from deepseek_code.session import BackupManager
        
        manager = BackupManager(sandbox_root)
        test_file = sandbox_root / "test.py"
        
        # Read original
        original = test_file.read_text()
        
        # Backup original
        manager.create_backup("test.py", original)
        
        # Modify file
        test_file.write_text("modified content")
        assert test_file.read_text() == "modified content"
        
        # Undo - should restore original
        result = manager.undo_last()
        assert result is not None
        assert test_file.read_text() == original
    
    def test_full_mode_cycle(self):
        """Test cycling through all modes."""
        from deepseek_code.session import SessionState
        
        state = SessionState()
        
        # Start in standard
        assert state.selected_mode == "standard"
        assert state.tools_enabled is True
        
        # Switch to safe
        state.apply_mode("safe")
        assert state.tools_enabled is False
        assert state.auto_approve is False
        
        # Switch to agent  
        state.apply_mode("agent")
        assert state.tools_enabled is True
        assert state.auto_approve is True
        
        # Switch to readonly
        state.apply_mode("readonly")
        assert state.readonly_mode is True
        
        # Back to standard
        state.apply_mode("standard")
        assert state.readonly_mode is False
        assert state.tools_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
