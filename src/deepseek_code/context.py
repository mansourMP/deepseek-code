"""
Context file management for DeepSeek Code.

Supports hierarchical DEEPSEEK.md files for project-specific instructions:
- ~/.deepseek/DEEPSEEK.md (global)
- /project/DEEPSEEK.md (project root)
- /project/src/DEEPSEEK.md (subdirectory)
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def find_context_files(start_path: Path) -> List[Path]:
    """
    Find all DEEPSEEK.md files from global to current directory.
    
    Returns files in order of precedence (global → project → local).
    
    Args:
        start_path: Current working directory
    
    Returns:
        List of context file paths, ordered from least to most specific
    """
    context_files: List[Path] = []
    
    # 1. Global context file
    global_context = Path.home() / ".deepseek" / "DEEPSEEK.md"
    if global_context.exists():
        context_files.append(global_context)
    
    # 2. Walk up from current directory to root, collecting DEEPSEEK.md files
    current = start_path.resolve()
    local_contexts: List[Path] = []
    
    for parent in [current] + list(current.parents):
        context_file = parent / "DEEPSEEK.md"
        if context_file.exists():
            local_contexts.append(context_file)
        
        # Stop at home directory
        if parent == Path.home():
            break
    
    # Reverse to get root → leaf order
    context_files.extend(reversed(local_contexts))
    
    return context_files


def load_context(start_path: Path) -> str:
    """
    Load and merge all context files into a single string.
    
    Files are concatenated in order of specificity, with headers
    indicating which file each section comes from.
    
    Args:
        start_path: Current working directory
    
    Returns:
        Merged context string
    """
    context_files = find_context_files(start_path)
    
    if not context_files:
        return ""
    
    sections: List[str] = []
    
    for context_file in context_files:
        try:
            content = context_file.read_text(encoding="utf-8", errors="replace")
            
            # Add header to identify source
            if context_file.parent == Path.home() / ".deepseek":
                header = "# Global Context (from ~/.deepseek/DEEPSEEK.md)"
            else:
                header = f"# Context from {context_file.parent}"
            
            sections.append(f"{header}\n\n{content.strip()}")
        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read
            continue
    
    return "\n\n---\n\n".join(sections)


def create_example_context_file(path: Path) -> Path:
    """
    Create an example DEEPSEEK.md file with helpful templates.
    
    Args:
        path: Directory to create the file in
    
    Returns:
        Path to created file
    """
    context_file = path / "DEEPSEEK.md"
    
    example_content = """# DeepSeek Code Context

This file provides context and instructions for the DeepSeek coding agent.
It will be automatically loaded when working in this directory.

## Project Overview

<!-- Describe your project here -->
This is a [Python/JavaScript/etc] project that...

## Architecture

<!-- Explain key architectural decisions -->
- **Backend:** FastAPI/Express/etc
- **Frontend:** React/Vue/etc
- **Database:** PostgreSQL/MongoDB/etc

## Coding Standards

<!-- Define your coding standards -->
- Use type hints for all Python functions
- Follow PEP 8 style guide
- Write docstrings for all public functions
- Prefer composition over inheritance

## Common Tasks

<!-- List frequent operations -->
- **Run tests:** `pytest tests/`
- **Start dev server:** `npm run dev`
- **Database migrations:** `alembic upgrade head`

## Important Files

<!-- Highlight key files -->
- `src/main.py` - Application entry point
- `src/config.py` - Configuration management
- `tests/` - Test suite

## Do's and Don'ts

<!-- Specific instructions for the AI -->
✅ DO:
- Always write tests for new features
- Use async/await for I/O operations
- Add type hints to function signatures

❌ DON'T:
- Don't modify files in `vendor/` directory
- Don't commit sensitive data
- Don't use `any` type in TypeScript

## Dependencies

<!-- List important dependencies -->
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation

## Notes

<!-- Any other important information -->
- This project uses Python 3.11+
- We follow semantic versioning
- All PRs require code review
"""
    
    context_file.write_text(example_content, encoding="utf-8")
    return context_file


def get_context_summary(start_path: Path) -> str:
    """
    Get a summary of loaded context files.
    
    Args:
        start_path: Current working directory
    
    Returns:
        Human-readable summary
    """
    context_files = find_context_files(start_path)
    
    if not context_files:
        return "No DEEPSEEK.md context files found"
    
    lines = ["Loaded context from:"]
    for cf in context_files:
        if cf.parent == Path.home() / ".deepseek":
            lines.append(f"  • Global: {cf}")
        else:
            lines.append(f"  • {cf}")
    
    return "\n".join(lines)
