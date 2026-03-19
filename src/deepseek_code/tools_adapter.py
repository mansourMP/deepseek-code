from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tools import (
    list_dir,
    read_file as ds_read_file,
    write_file as ds_write_file,
    search as ds_search,
    glob_files as ds_glob_files,
    run_shell as ds_run_shell,
)

class ToolsAdapter:
    """
    Adapter for the Codex-grade orchestrator to use the existing tool surface.
    """

    def __init__(self, root_path: str | Path, denylist: List[str] = None):
        self.root = Path(root_path).resolve()
        self.denylist = denylist or []
        self.cwd = self.root

    def list_directory(self, dir_path: str, file_filtering_options: dict = None,
                       ignore: List[str] = None) -> Dict[str, Any]:
        res = list_dir(self.root, dir_path, self.cwd)
        if res.metadata.get("path"):
             # Update internal CWD tracker if we were to support it
             pass
        return {
            "dir_path": dir_path,
            "entries": res.output.splitlines() if not res.is_error else [],
            "error": res.output if res.is_error else None
        }

    def read_file(self, file_path: str, limit: int = None, offset: int = None) -> Dict[str, Any]:
        # Note: Existing read_file doesn't support limit/offset directly, 
        # but we can implement it here.
        res = ds_read_file(self.root, file_path, self.cwd)
        if res.is_error:
            return {"file_path": file_path, "error": res.output}
        
        content = res.output
        lines = content.splitlines()
        
        start = offset or 0
        end = (start + limit) if limit is not None else len(lines)
        
        chunk = "\n".join(lines[start:end])
        return {
            "file_path": file_path,
            "offset": start,
            "limit": limit,
            "content": chunk,
            "total_lines": len(lines)
        }

    def search_file_content(self, pattern: str, dir_path: str = None, include: str = None,
                            context: int = 2, fixed_strings: bool = False,
                            case_sensitive: bool = False) -> Dict[str, Any]:
        # Map parameters to ds_search
        import re
        effective_pattern = re.escape(pattern) if fixed_strings else pattern
        if not case_sensitive:
            effective_pattern = f"(?i){effective_pattern}"
            
        res = ds_search(self.root, effective_pattern, include or dir_path, self.cwd)
        
        matches = []
        if not res.is_error and res.output != "No matches":
            for line in res.output.splitlines():
                # format is "rel:idx: line"
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    matches.append({
                        "file": parts[0],
                        "line": int(parts[1]),
                        "snippet": parts[2].strip()
                    })
        
        return {"pattern": pattern, "matches": matches[:20], "error": res.output if res.is_error else None}

    def glob(self, pattern: str, dir_path: str = None) -> Dict[str, Any]:
        # Note: ds_glob_files uses cwd or root. 
        # If dir_path is provided, we temporarily change context or handle it.
        search_base = Path(dir_path).resolve() if dir_path else self.cwd
        res = ds_glob_files(self.root, pattern, search_base)
        
        paths = []
        if not res.is_error and res.output != "No files found":
            paths = res.output.splitlines()
            
        return {"pattern": pattern, "paths": paths, "error": res.output if res.is_error else None}

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        res = ds_write_file(self.root, file_path, content, self.cwd)
        return {
            "file_path": file_path, 
            "bytes": len(content.encode("utf-8")),
            "error": res.output if res.is_error else None
        }

    def run_shell_command(self, command: str, description: str = None, dir_path: str = None) -> Dict[str, Any]:
        exec_cwd = Path(dir_path).resolve() if dir_path else self.cwd
        res = ds_run_shell(self.root, command, self.denylist, exec_cwd)
        
        # If metadata has new_cwd, update our tracking (though orchestrator might manage it)
        if res.metadata.get("new_cwd"):
            self.cwd = Path(res.metadata["new_cwd"])

        return {
            "command": command,
            "cwd": str(exec_cwd),
            "exit_code": 1 if res.is_error else 0,
            "stdout": res.output if not res.is_error else "",
            "stderr": res.output if res.is_error else "",
            "new_cwd": str(self.cwd)
        }
