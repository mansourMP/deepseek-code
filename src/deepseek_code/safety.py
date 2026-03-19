"""
Security and sandboxing for DeepSeek Code.

Provides comprehensive protection against:
- Path traversal attacks
- Command injection
- Resource exhaustion
- Dangerous operations
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# DENYLIST - Commands and patterns that are never allowed
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_DENYLIST = [
    # Destructive file operations
    "rm -rf",
    "rm -fr",
    "rmdir",

    # Privilege escalation
    "sudo",
    "su ",
    "doas",

    # System destructive
    "dd if=",
    "mkfs",
    "fdisk",
    "parted",

    # Fork bombs and resource exhaustion
    ":(){ :|:& };:",

    # Permission changes (recursive)
    "chmod -r",
    "chmod -R",
    "chown -r",
    "chown -R",

    # Network exfiltration
    "curl.*>",
    "wget.*-O",
    "nc -e",
    "netcat",

    # History/credential theft
    ".bash_history",
    ".zsh_history",
    ".ssh/",
    ".aws/",
    ".config/",

    # Dangerous redirects
    "> /dev/sd",
    "> /dev/hd",
    "> /dev/null",  # Usually benign but can hide errors

    # Process manipulation
    "kill -9",
    "killall",
    "pkill",

    # System shutdown/reboot
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
]

# Directories that should never be accessed
BLOCKED_DIRECTORIES: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".env",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",
}

# File patterns that should never be read/written
SENSITIVE_FILE_PATTERNS = [
    r"\.env$",
    r"\.env\..*$",
    r"\.pem$",
    r"\.key$",
    r"\.crt$",
    r"id_rsa",
    r"id_ed25519",
    r"\.secrets?$",
    r"credentials",
    r"password",
    r"\.aws/",
    r"\.ssh/",
]


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SandboxError(ValueError):
    """Raised when a security violation is detected."""
    pass


class CommandDeniedError(SandboxError):
    """Raised when a command is blocked by denylist."""
    pass


class PathEscapeError(SandboxError):
    """Raised when a path escapes the sandbox."""
    pass


class SensitiveFileError(SandboxError):
    """Raised when accessing a sensitive file."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# PATH VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_path(root: Path, target: str | Path) -> Path:
    """
    Safely resolve a path within the sandbox root.
    
    Args:
        root: The sandbox root directory
        target: The target path (relative or absolute)
    
    Returns:
        The resolved absolute path
    
    Raises:
        PathEscapeError: If the path escapes the sandbox
    """
    root = root.resolve()
    target_path = Path(target)

    # Handle relative and absolute paths
    if not target_path.is_absolute():
        target_path = (root / target_path).resolve()
    else:
        target_path = target_path.resolve()

    # Verify path is within sandbox
    try:
        if target_path != root:
            target_path.relative_to(root)
    except ValueError as exc:
        raise PathEscapeError(f"Path escapes sandbox: {target}") from exc

    return target_path


def is_path_safe(root: Path, target: str | Path) -> bool:
    """Check if a path is safe without raising exceptions."""
    try:
        resolve_path(root, target)
        return True
    except (SandboxError, ValueError):
        return False


def check_path_components(path: Path) -> None:
    """
    Check path components for blocked directories.
    
    Raises:
        PathEscapeError: If path contains blocked directories
    """
    for part in path.parts:
        if part in BLOCKED_DIRECTORIES:
            raise PathEscapeError(f"Access to blocked directory: {part}")


def is_sensitive_file(path: Path) -> bool:
    """Check if a file matches sensitive patterns."""
    path_str = str(path).lower()
    for pattern in SENSITIVE_FILE_PATTERNS:
        if re.search(pattern, path_str, re.IGNORECASE):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_command_allowed(command: str, denylist: Iterable[str]) -> bool:
    """
    Check if a shell command is allowed.
    
    Args:
        command: The command to check
        denylist: List of denied patterns
    
    Returns:
        True if allowed, False if denied
    """
    lowered = command.lower()

    for entry in denylist:
        if entry.lower() in lowered:
            return False

    return True


def sanitize_command(command: str) -> str:
    """
    Sanitize a shell command and check for injection patterns.
    
    Returns the command if safe, raises CommandDeniedError if not.
    """
    dangerous_patterns = [
        # Command chaining
        (r';\s*(rm|sudo|dd|mkfs)', "Command chaining with dangerous command"),
        (r'\|\s*(rm|sudo|dd|mkfs)', "Pipe to dangerous command"),
        (r'&&\s*(rm|sudo|dd|mkfs)', "Conditional dangerous command"),

        # Command substitution
        (r'`[^`]*`', "Backtick command substitution"),
        (r'\$\([^)]+\)', "Dollar-paren command substitution"),

        # Reverse shells
        (r'/bin/bash\s+-i', "Interactive bash shell"),
        (r'/bin/sh\s+-i', "Interactive shell"),
        (r'bash\s+-c.*nc\s', "Netcat in bash"),

        # Environment manipulation
        (r'export\s+PATH=', "PATH manipulation"),
        (r'export\s+LD_', "Library path manipulation"),
    ]

    for pattern, description in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise CommandDeniedError(f"Dangerous pattern detected: {description}")

    return command


def effective_denylist(extra: list[str] | None = None) -> list[str]:
    """
    Get the combined denylist with defaults and custom entries.
    
    Args:
        extra: Additional entries to add to denylist
    
    Returns:
        Combined list of denied patterns
    """
    merged = list(DEFAULT_DENYLIST)
    if extra:
        merged.extend(extra)
    return merged


# ═══════════════════════════════════════════════════════════════════════════════
# FILE SIZE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_file_size(path: Path, max_bytes: int) -> None:
    """
    Ensure a file is within size limits.
    
    Raises:
        SandboxError: If file exceeds size limit
    """
    if not path.exists():
        return

    size = path.stat().st_size
    if size > max_bytes:
        size_mb = size / (1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        raise SandboxError(
            f"File too large: {path.name} ({size_mb:.1f}MB > {max_mb:.1f}MB limit)"
        )


def check_disk_space(path: Path, required_bytes: int) -> bool:
    """Check if there's enough disk space for an operation."""
    try:
        import os
        stat = os.statvfs(path)
        available = stat.f_frsize * stat.f_bavail
        return available > required_bytes
    except (OSError, AttributeError):
        # statvfs not available on Windows, assume OK
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# SYMLINK SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

def check_symlink_safety(root: Path, path: Path) -> None:
    """
    Check that symlinks don't point outside the sandbox.
    
    Raises:
        PathEscapeError: If symlink escapes sandbox
    """
    if not path.is_symlink():
        return

    # Resolve the symlink target
    try:
        target = path.resolve()
        target.relative_to(root.resolve())
    except ValueError:
        raise PathEscapeError(f"Symlink escapes sandbox: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE SAFETY CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def validate_file_operation(
    root: Path,
    path: str | Path,
    operation: str = "access",
    max_size: int | None = None,
) -> Path:
    """
    Comprehensive validation for file operations.
    
    Args:
        root: Sandbox root directory
        path: Target path
        operation: Type of operation (read, write, delete)
        max_size: Maximum file size for read operations
    
    Returns:
        Resolved, validated path
    
    Raises:
        SandboxError: If any validation fails
    """
    # Resolve and validate path
    resolved = resolve_path(root, path)

    # Check for blocked directories
    check_path_components(resolved)

    # Check symlink safety
    if resolved.exists():
        check_symlink_safety(root, resolved)

    # Check sensitive files for read/write
    if operation in ("read", "write") and is_sensitive_file(resolved):
        raise SensitiveFileError(f"Cannot {operation} sensitive file: {path}")

    # Check file size for reads
    if operation == "read" and max_size and resolved.exists():
        ensure_file_size(resolved, max_size)

    return resolved


def validate_shell_command(
    command: str,
    denylist: list[str],
) -> str:
    """
    Comprehensive validation for shell commands.
    
    Args:
        command: Shell command to validate
        denylist: Custom denylist entries
    
    Returns:
        Validated command
    
    Raises:
        CommandDeniedError: If command is not allowed
    """
    # Check against denylist
    if not is_command_allowed(command, denylist):
        raise CommandDeniedError(f"Command denied by denylist: {command}")

    # Check for injection patterns
    sanitize_command(command)

    return command


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT ROOT & STATUS DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_git_branch(root: Path) -> str:
    """Get the current git branch name."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip() or "no-branch"
    except Exception:
        return "n/a"


def get_trust_status(root: Path) -> str:
    """Check if the workspace is trusted."""
    if (root / ".env").exists() or (root / "pyproject.toml").exists():
        return "trusted"
    return "untrusted"


def find_project_root(start_path: Path | None = None) -> Path:
    """
    Find the project root directory.
    
    Prioritizes .git directory to handle monorepos correctly.
    Otherwise finds the nearest project marker.
    """
    current = (start_path or Path.cwd()).resolve()

    # Check for .git specifically first (traverse up)
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent

    # Markers that indicate project root
    root_markers = [
        ".deepseek-code.json",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Makefile",
    ]

    # Search upward through parent directories
    for parent in [current] + list(current.parents):
        for marker in root_markers:
            if (parent / marker).exists():
                return parent

    # No markers found, use start path
    return current
