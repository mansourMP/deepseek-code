from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .safety import SandboxError, effective_denylist, ensure_file_size, is_command_allowed, resolve_path

MAX_READ_BYTES = 2 * 1024 * 1024
MAX_SEARCH_RESULTS = 200
SHELL_TIMEOUT = 30
ALLOWLIST_ROOT = Path("/Users/mansur/universal_study_bot org/backend/content/packs").resolve()


@dataclass
class ToolResult:
    output: str
    is_error: bool = False
    denied: bool = False
    metadata: Dict[str, Any] = None  # Store state changes like new_cwd

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def _get_target(root: Path, path: str | None, cwd: Path | None) -> Path:
    """Helper to resolve path relative to CWD if provided, then verify safety against root."""
    path_str = path or "."
    path_obj = Path(path_str)
    
    if path_obj.is_absolute():
        return resolve_path(root, path_obj)
    
    base = cwd or root
    return resolve_path(root, base / path_obj)


def list_dir(root: Path, path: str | None, cwd: Path | None = None) -> ToolResult:
    try:
        target = _get_target(root, path, cwd)
        if not target.exists():
            return ToolResult(f"Path not found: {path}", is_error=True)
        if not target.is_dir():
            return ToolResult(f"Not a directory: {path}", is_error=True)
        
        entries = []
        for item in sorted(target.iterdir()):
            suffix = "/" if item.is_dir() else ""
            entries.append(f"{item.name}{suffix}")
        
        output = "\n".join(entries)
        
        # Add a subtle hint to prevent looping if the user didn't ask for this specifically
        # This is a passive environment feature
        return ToolResult(output, metadata={"path": str(target)})
    except SandboxError as exc:
        return ToolResult(str(exc), is_error=True)


def read_file(root: Path, path: str, cwd: Path | None = None) -> ToolResult:
    try:
        target = _get_target(root, path, cwd)
        if not target.exists():
            return ToolResult(f"Path not found: {path}", is_error=True)
        if target.is_dir():
            return ToolResult(f"Not a file: {path}", is_error=True)
        ensure_file_size(target, MAX_READ_BYTES)
        content = target.read_text(encoding="utf-8", errors="replace")
        return ToolResult(content)
    except SandboxError as exc:
        msg = str(exc)
        if "too large" in msg:
            msg = f"CRITICAL: {msg}\nACTION REQUIRED: This file is too large for 'read_file'. Use 'run_shell' with 'grep', 'head', or 'tail' to inspect it, or 'read_json_chunk' if it is a JSON array. Do not attempt 'read_file' again for this path."
        return ToolResult(msg, is_error=True)


def write_file(root: Path, path: str, content: str, cwd: Path | None = None) -> ToolResult:
    try:
        target = _get_target(root, path, cwd)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(f"Wrote {len(content)} bytes to {path}")
    except SandboxError as exc:
        return ToolResult(str(exc), is_error=True)


def delete_file(root: Path, path: str, cwd: Path | None = None) -> ToolResult:
    try:
        target = _get_target(root, path, cwd)
        if not target.exists():
            return ToolResult(f"Path not found: {path}", is_error=True)
        if target.is_dir():
            return ToolResult(f"Not a file: {path}", is_error=True)
        target.unlink()
        return ToolResult(f"Deleted {path}")
    except SandboxError as exc:
        return ToolResult(str(exc), is_error=True)


def _allowlist_check(target: Path) -> None:
    try:
        target.relative_to(ALLOWLIST_ROOT)
    except ValueError as exc:
        raise SandboxError(f"Path not in allowlist: {target}") from exc


def read_json_chunk(root: Path, path: str, start: int, count: int, cwd: Path | None = None) -> ToolResult:
    try:
        import ijson
    except ImportError:
        return ToolResult("ijson not installed", is_error=True)
    try:
        if start < 0 or count < 0:
            return ToolResult("start/count must be non-negative", is_error=True)
        target = _get_target(root, path, cwd)
        _allowlist_check(target)
        if not target.exists():
            return ToolResult(f"Path not found: {path}", is_error=True)
        if target.is_dir():
            return ToolResult(f"Not a file: {path}", is_error=True)
        ensure_file_size(target, MAX_READ_BYTES)
        items: List[dict] = []
        with target.open("rb") as handle:
            for idx, item in enumerate(ijson.items(handle, "item")):
                if idx < start:
                    continue
                if idx >= start + count:
                    break
                items.append(item)
        payload = {"start": start, "count": len(items), "items": items}
        return ToolResult(json.dumps(payload, ensure_ascii=True, indent=2))
    except SandboxError as exc:
        return ToolResult(str(exc), is_error=True)


def write_json_chunk(root: Path, path: str, start: int, items: List[dict], cwd: Path | None = None) -> ToolResult:
    try:
        import ijson
    except ImportError:
        return ToolResult("ijson not installed", is_error=True)
    try:
        if start < 0:
            return ToolResult("start must be non-negative", is_error=True)
        target = _get_target(root, path, cwd)
        _allowlist_check(target)
        if not target.exists():
            return ToolResult(f"Path not found: {path}", is_error=True)
        if target.is_dir():
            return ToolResult(f"Not a file: {path}", is_error=True)
        temp_path = target.with_suffix(target.suffix + ".tmp")
        with target.open("rb") as inp, temp_path.open("w", encoding="utf-8") as out:
            out.write("[\n")
            first = True
            replaced = 0
            for idx, item in enumerate(ijson.items(inp, "item")):
                if start <= idx < start + len(items):
                    item = items[idx - start]
                    replaced += 1
                text = json.dumps(item, ensure_ascii=True, indent=2)
                indented = "\n".join("  " + line for line in text.splitlines())
                if not first:
                    out.write(",\n")
                out.write(indented)
                first = False
            out.write("\n]\n")
        temp_path.replace(target)
        if replaced != len(items):
            return ToolResult("Slice length mismatch", is_error=True)
        return ToolResult(f"Updated {len(items)} items at {path} starting {start}")
    except SandboxError as exc:
        return ToolResult(str(exc), is_error=True)


def search(root: Path, pattern: str, path_or_glob: str | None, cwd: Path | None = None) -> ToolResult:
    try:
        base = _get_target(root, path_or_glob or ".", cwd)
    except SandboxError:
        base = cwd or root
    matcher = re.compile(pattern)
    results: List[str] = []

    paths: List[Path] = []
    if path_or_glob and any(ch in path_or_glob for ch in "*?[]"):
        search_root = cwd or root
        for item in search_root.glob(path_or_glob):
            if item.is_file():
                paths.append(item)
    elif base.is_file():
        paths.append(base)
    else:
        for item in base.rglob("*"):
            if item.is_file():
                paths.append(item)

    for file_path in paths:
        try:
            ensure_file_size(file_path, MAX_READ_BYTES)
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if matcher.search(line):
                # Show path relative to CWD if possible, else root
                try:
                    rel = file_path.relative_to(cwd or root)
                except ValueError:
                    rel = file_path.relative_to(root)
                results.append(f"{rel}:{idx}: {line}")
                if len(results) >= MAX_SEARCH_RESULTS:
                    return ToolResult("\n".join(results))
    return ToolResult("\n".join(results) if results else "No matches")


def glob_files(root: Path, pattern: str, cwd: Path | None = None) -> ToolResult:
    """Find files matching a glob pattern."""
    try:
        search_base = cwd or root
        results = []
        for p in search_base.glob(pattern):
            try:
                rel = p.relative_to(search_base)
                results.append(str(rel))
            except ValueError:
                results.append(str(p))
        return ToolResult("\n".join(sorted(results)) if results else "No files found")
    except Exception as e:
        return ToolResult(f"Glob error: {e}", is_error=True)


def run_shell(root: Path, command: str, denylist: List[str], cwd: Path | None = None) -> ToolResult:
    if not is_command_allowed(command, denylist):
        return ToolResult("Command blocked by denylist", is_error=True)
    
    # Use provided CWD or fallback to root
    working_dir = cwd or root
    
    # Handle "cd" commands specifically
    # Support chaining like "cd foo && pwd" or "cd foo; ls"
    clean_cmd = command.strip()
    is_cd = False
    cd_target = ""
    remaining_cmd = ""
    
    if clean_cmd.startswith("cd ") or clean_cmd == "cd":
        is_cd = True
        # Split by && or ; to separate the cd portion
        # valid separators for cd: '&&', ';'
        # We take the first one found
        separators = ["&&", ";"]
        first_sep_idx = -1
        sep_len = 0
        
        for sep in separators:
            idx = clean_cmd.find(sep)
            if idx != -1:
                if first_sep_idx == -1 or idx < first_sep_idx:
                    first_sep_idx = idx
                    sep_len = len(sep)
        
        if first_sep_idx != -1:
            cd_part = clean_cmd[:first_sep_idx].strip()
            remaining_cmd = clean_cmd[first_sep_idx + sep_len:].strip()
        else:
            cd_part = clean_cmd
            remaining_cmd = ""
            
        cmd_parts = cd_part.split()
        if len(cmd_parts) > 1:
             # Re-join to handle spaces in path if strictly cd part
             cd_target = " ".join(cmd_parts[1:]).strip('"\'')
        else:
             # "cd" alone -> root or home? Let's assume root of project for safety or stay put
             # Standard shell "cd" goes home. Here we might just stay in project root.
             cd_target = "" 

    if is_cd:
        try:
            target_path = cd_target
            if not target_path:
                 # cd with no args -> go to project root
                 new_path = root
            else:
                # Handle basic relative paths
                new_path = (working_dir / target_path).resolve()
            
            if not new_path.exists():
                return ToolResult(f"cd: no such file or directory: {target_path}", is_error=True)
            if not new_path.is_dir():
                return ToolResult(f"cd: not a directory: {target_path}", is_error=True)
            
            # Verify safety (stay within root? optional, but good for safety)
            # For a "powerful" environment, we might allow full system traversal if approved.
            
            # If there is a remaining command, execute it in the NEW cwd
            output_msg = f"Changed directory to {new_path}"
            
            if remaining_cmd:
                # Recursively run the rest
                # We can't easily recurse cleanly because we need to combine results.
                # So we run subprocess here.
                completed = subprocess.run(
                    remaining_cmd,
                    shell=True,
                    cwd=new_path,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=SHELL_TIMEOUT,
                )
                rest_out = (completed.stdout or "") + (completed.stderr or "")
                output_msg += f"\n{rest_out}"
                
                if completed.returncode != 0:
                     return ToolResult(
                        output_msg, 
                        is_error=True, 
                        metadata={"new_cwd": str(new_path)}
                    )

            return ToolResult(
                output_msg + f"\nSYSTEM ALERT: Navigation successful. You are now in {new_path}.", 
                metadata={"new_cwd": str(new_path)}
            )
        except Exception as e:
            return ToolResult(f"cd failed: {e}", is_error=True)

    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=SHELL_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return ToolResult("Command timed out", is_error=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        return ToolResult(output or f"Command failed with {completed.returncode}", is_error=True)
    return ToolResult(output.strip() or "Command completed")


def tool_schemas(allowed: set[str] | None = None) -> List[Dict[str, Any]]:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files in a directory. Use ONLY if you are unsure of the file structure. Prefer glob_files.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "Delete a file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_json_chunk",
                "description": "Read a slice from a JSON array file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start": {"type": "integer"},
                        "count": {"type": "integer"},
                    },
                    "required": ["path", "start", "count"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_json_chunk",
                "description": "Write a slice back into a JSON array file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start": {"type": "integer"},
                        "items": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["path", "start", "items"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search files for a regex pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "path_or_glob": {"type": "string"},
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "glob_files",
                "description": "Find files matching a glob pattern (e.g., '**/*.py')",
                "parameters": {
                    "type": "object",
                    "properties": {"pattern": {"type": "string"}},
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_shell",
                "description": "Run a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                    "required": ["cmd"],
                },
            },
        },
    ]
    if allowed is None:
        return tools
    return [tool for tool in tools if tool["function"]["name"] in allowed]


def dispatch_tool(
    root: Path,
    name: str,
    arguments: Dict[str, Any],
    denylist: List[str],
    cwd: Path | None = None,
) -> ToolResult:
    if name == "list_dir":
        return list_dir(root, arguments.get("path"), cwd)
    if name == "read_file":
        return read_file(root, arguments["path"], cwd)
    if name == "write_file":
        return write_file(root, arguments["path"], arguments["content"], cwd)
    if name == "delete_file":
        return delete_file(root, arguments["path"], cwd)
    if name == "read_json_chunk":
        return read_json_chunk(root, arguments["path"], arguments["start"], arguments["count"], cwd)
    if name == "write_json_chunk":
        return write_json_chunk(root, arguments["path"], arguments["start"], arguments["items"], cwd)
    if name == "search":
        return search(root, arguments["pattern"], arguments.get("path_or_glob"), cwd)
    if name == "glob_files":
        return glob_files(root, arguments["pattern"], cwd)
    if name == "run_shell":
        return run_shell(root, arguments["cmd"], denylist, cwd)
    return ToolResult(f"Unknown tool: {name}", is_error=True)


def parse_tool_arguments(raw: str) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        return json.loads(raw or "{}"), None
    except json.JSONDecodeError as exc:
        return None, str(exc)
