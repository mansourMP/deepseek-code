from pathlib import Path
import os

root = Path("/Users/mansur/deepseek code")
cwd = root / "src/deepseek_code"

print(f"Root: {root}")
print(f"CWD: {cwd}")
print(f"Exists: {cwd.exists()}")
print(f"Is Dir: {cwd.is_dir()}")

def glob_files(root: Path, pattern: str, cwd: Path | None = None):
    try:
        search_base = cwd or root
        print(f"Search Base: {search_base}")
        results = []
        for p in search_base.glob(pattern):
            try:
                rel = p.relative_to(search_base)
                results.append(str(rel))
            except ValueError:
                results.append(str(p))
        return "\n".join(sorted(results)) if results else "No files found"
    except Exception as e:
        return f"Glob error: {e}"

print("--- Glob *.py ---")
print(glob_files(root, "*.py", cwd))

print("--- Glob **/*.py ---")
print(glob_files(root, "**/*.py", cwd))
