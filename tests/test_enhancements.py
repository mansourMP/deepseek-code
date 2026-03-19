"""
Tests for project root detection and model selection.
"""

from pathlib import Path
import tempfile
import shutil

import pytest


class TestProjectRootDetection:
    """Test find_project_root functionality."""
    
    def test_finds_git_root(self, tmp_path: Path):
        """Should find .git directory as project root."""
        from deepseek_code.safety import find_project_root
        
        # Create structure: root/.git and root/subdir/deep
        root = tmp_path / "project"
        root.mkdir()
        (root / ".git").mkdir()
        
        subdir = root / "subdir" / "deep"
        subdir.mkdir(parents=True)
        
        # Should find root from deep subdirectory
        found = find_project_root(subdir)
        assert found == root
    
    def test_finds_deepseek_config(self, tmp_path: Path):
        """Should find .deepseek-code.json as project root."""
        from deepseek_code.safety import find_project_root
        
        root = tmp_path / "project"
        root.mkdir()
        (root / ".deepseek-code.json").write_text("{}")
        
        subdir = root / "src" / "module"
        subdir.mkdir(parents=True)
        
        found = find_project_root(subdir)
        assert found == root
    
    def test_finds_pyproject_toml(self, tmp_path: Path):
        """Should find pyproject.toml as project root."""
        from deepseek_code.safety import find_project_root
        
        root = tmp_path / "project"
        root.mkdir()
        (root / "pyproject.toml").write_text("")
        
        subdir = root / "tests"
        subdir.mkdir()
        
        found = find_project_root(subdir)
        assert found == root
    
    def test_finds_package_json(self, tmp_path: Path):
        """Should find package.json as project root."""
        from deepseek_code.safety import find_project_root
        
        root = tmp_path / "project"
        root.mkdir()
        (root / "package.json").write_text("{}")
        
        subdir = root / "src" / "components"
        subdir.mkdir(parents=True)
        
        found = find_project_root(subdir)
        assert found == root
    
    def test_returns_start_path_if_no_markers(self, tmp_path: Path):
        """Should return start path if no markers found."""
        from deepseek_code.safety import find_project_root
        
        # No markers anywhere
        subdir = tmp_path / "random" / "path"
        subdir.mkdir(parents=True)
        
        found = find_project_root(subdir)
        # Should return the resolved start path
        assert found == subdir.resolve()
    
    def test_finds_nearest_marker(self, tmp_path: Path):
        """Should find nearest marker when multiple exist."""
        from deepseek_code.safety import find_project_root
        
        # Create nested structure with multiple markers
        outer = tmp_path / "outer"
        outer.mkdir()
        (outer / ".git").mkdir()
        
        inner = outer / "inner"
        inner.mkdir()
        (inner / "package.json").write_text("{}")
        
        subdir = inner / "src"
        subdir.mkdir()
        
        # Should find inner (nearest marker) not outer
        found = find_project_root(subdir)
        assert found == inner


class TestModelSelection:
    """Test model selection enhancements."""
    
    def test_model_command_without_args_shows_list(self, mock_console, sandbox_root):
        """Calling /model without args should list models."""
        from deepseek_code.ui.commands import cmd_model, CommandContext
        from deepseek_code.ui.themes import get_theme
        from unittest.mock import Mock, patch
        
        # Mock the API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "deepseek-chat"},
                {"id": "deepseek-coder"},
            ]
        }
        
        ctx = _make_test_context(mock_console, sandbox_root)
        
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            result = cmd_model(ctx, "")
        
        # Should have printed something
        assert mock_console.print.called
    
    def test_model_selection_by_number(self, mock_console, sandbox_root):
        """Should allow selecting model by number."""
        from deepseek_code.ui.commands import cmd_model
        from unittest.mock import Mock, patch
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "deepseek-chat"},
                {"id": "deepseek-coder"},
                {"id": "deepseek-reasoner"},
            ]
        }
        
        ctx = _make_test_context(mock_console, sandbox_root)
        
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            result = cmd_model(ctx, "2")
        
        # Should have set model to second one (deepseek-coder)
        assert ctx.agent.settings.model == "deepseek-coder"
    
    def test_model_selection_by_name(self, mock_console, sandbox_root):
        """Should allow selecting model by name."""
        from deepseek_code.ui.commands import cmd_model
        
        ctx = _make_test_context(mock_console, sandbox_root)
        result = cmd_model(ctx, "deepseek-reasoner")
        
        assert ctx.agent.settings.model == "deepseek-reasoner"


@pytest.fixture
def mock_console():
    """Create a mock console."""
    from unittest.mock import Mock
    console = Mock()
    console.print = Mock()
    return console


@pytest.fixture
def sandbox_root(tmp_path: Path) -> Path:
    """Create a sandbox directory."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return sandbox


def _make_test_context(console, root):
    """Helper to create test context."""
    from deepseek_code.ui.commands import CommandContext
    from deepseek_code.ui.themes import get_theme
    from unittest.mock import Mock
    
    agent = Mock()
    agent.messages = []
    agent.settings = Mock()
    agent.settings.model = "deepseek-chat"
    
    return CommandContext(
        console=console,
        agent=agent,
        root=root,
        model_name="deepseek-chat",
        api_key="test-key",
        base_url="https://api.deepseek.com",
        theme=get_theme(),
        auto_approve=False,
        tools_enabled=True,
        readonly_mode=False,
        debug=False,
        approve_reads_enabled=False,
        selected_mode="standard",
        delay_ms=0,
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
