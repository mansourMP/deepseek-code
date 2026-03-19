from pathlib import Path

import pytest

from deepseek_code.safety import SandboxError, effective_denylist, is_command_allowed, resolve_path


def test_resolve_path_blocks_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(SandboxError):
        resolve_path(root, "../outside.txt")


def test_resolve_path_allows_inside(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = resolve_path(root, "file.txt")
    assert target == root / "file.txt"


def test_denylist_blocks_rm_rf() -> None:
    denylist = effective_denylist([])
    assert not is_command_allowed("rm -rf /", denylist)
    assert is_command_allowed("ls -la", denylist)
