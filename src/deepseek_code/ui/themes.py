"""
Premium theming system for DS Code Agent.

Provides customizable color schemes with predefined themes inspired
by popular development environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Theme:
    """Immutable theme configuration."""

    name: str

    # Core colors
    primary: str
    secondary: str
    accent: str

    # Semantic colors
    success: str
    warning: str
    error: str
    info: str

    # UI colors
    dim: str
    muted: str
    background: str
    foreground: str

    # Component-specific
    prompt: str
    assistant: str
    tool_read: str
    tool_write: str
    tool_delete: str
    tool_shell: str

    # Diff colors
    diff_add: str
    diff_remove: str
    diff_context: str

    # Panel borders
    border_primary: str
    border_secondary: str
    border_success: str
    border_warning: str
    border_error: str

    def to_rich_style(self, component: str) -> str:
        """Get Rich style string for a component."""
        return getattr(self, component, self.foreground)

    def get_tool_style(self, tool_name: str) -> str:
        """Get style for a specific tool."""
        if tool_name in {"read_file", "list_dir", "search", "read_json_chunk"}:
            return self.tool_read
        if tool_name in {"write_file", "write_json_chunk"}:
            return self.tool_write
        if tool_name == "delete_file":
            return self.tool_delete
        if tool_name == "run_shell":
            return self.tool_shell
        return self.muted


# ═══════════════════════════════════════════════════════════════════════════════
# PREDEFINED THEMES
# ═══════════════════════════════════════════════════════════════════════════════

THEMES: Dict[str, Theme] = {

    # ───────────────────────────────────────────────────────────────────────────
    # DeepSeek Default - Futuristic cyan/purple theme
    # ───────────────────────────────────────────────────────────────────────────
    "deepseek": Theme(
        name="DeepSeek",
        primary="#00D9FF",       # Bright cyan
        secondary="#7B61FF",     # Electric purple
        accent="#FF6B9D",        # Pink accent
        success="#00FF9F",       # Neon green
        warning="#FFB800",       # Amber
        error="#FF3B6D",         # Hot pink/red
        info="#60A5FA",          # Sky blue
        dim="#6B7280",           # Gray 500
        muted="#9CA3AF",         # Gray 400
        background="#0F172A",    # Slate 900
        foreground="#F1F5F9",    # Slate 100
        prompt="#00D9FF",        # Cyan prompt
        assistant="#A78BFA",     # Lavender
        tool_read="#60A5FA",     # Blue for reads
        tool_write="#34D399",    # Emerald for writes
        tool_delete="#F87171",   # Red for deletes
        tool_shell="#FBBF24",    # Amber for shell
        diff_add="#10B981",      # Emerald 500
        diff_remove="#EF4444",   # Red 500
        diff_context="#6B7280",  # Gray 500
        border_primary="#00D9FF",
        border_secondary="#7B61FF",
        border_success="#00FF9F",
        border_warning="#FFB800",
        border_error="#FF3B6D",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # GitHub Dark - Familiar GitHub look
    # ───────────────────────────────────────────────────────────────────────────
    "github": Theme(
        name="GitHub Dark",
        primary="#58A6FF",       # GitHub blue
        secondary="#A371F7",     # GitHub purple
        accent="#F78166",        # GitHub orange
        success="#3FB950",       # GitHub green
        warning="#D29922",       # GitHub yellow
        error="#F85149",         # GitHub red
        info="#58A6FF",          # GitHub blue
        dim="#484F58",           # Gray
        muted="#8B949E",         # Muted text
        background="#0D1117",    # GitHub bg
        foreground="#C9D1D9",    # GitHub text
        prompt="#58A6FF",
        assistant="#A371F7",
        tool_read="#58A6FF",
        tool_write="#3FB950",
        tool_delete="#F85149",
        tool_shell="#D29922",
        diff_add="#3FB950",
        diff_remove="#F85149",
        diff_context="#484F58",
        border_primary="#58A6FF",
        border_secondary="#A371F7",
        border_success="#3FB950",
        border_warning="#D29922",
        border_error="#F85149",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Dracula - Popular dark theme
    # ───────────────────────────────────────────────────────────────────────────
    "dracula": Theme(
        name="Dracula",
        primary="#BD93F9",       # Purple
        secondary="#FF79C6",     # Pink
        accent="#8BE9FD",        # Cyan
        success="#50FA7B",       # Green
        warning="#FFB86C",       # Orange
        error="#FF5555",         # Red
        info="#8BE9FD",          # Cyan
        dim="#6272A4",           # Comment
        muted="#F8F8F2",         # Foreground
        background="#282A36",    # Background
        foreground="#F8F8F2",    # Foreground
        prompt="#BD93F9",
        assistant="#FF79C6",
        tool_read="#8BE9FD",
        tool_write="#50FA7B",
        tool_delete="#FF5555",
        tool_shell="#FFB86C",
        diff_add="#50FA7B",
        diff_remove="#FF5555",
        diff_context="#6272A4",
        border_primary="#BD93F9",
        border_secondary="#FF79C6",
        border_success="#50FA7B",
        border_warning="#FFB86C",
        border_error="#FF5555",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Nord - Arctic, bluish color palette
    # ───────────────────────────────────────────────────────────────────────────
    "nord": Theme(
        name="Nord",
        primary="#88C0D0",       # Frost
        secondary="#81A1C1",     # Frost 2
        accent="#B48EAD",        # Aurora purple
        success="#A3BE8C",       # Aurora green
        warning="#EBCB8B",       # Aurora yellow
        error="#BF616A",         # Aurora red
        info="#5E81AC",          # Frost deep
        dim="#4C566A",           # Polar Night
        muted="#D8DEE9",         # Snow Storm
        background="#2E3440",    # Polar Night
        foreground="#ECEFF4",    # Snow Storm
        prompt="#88C0D0",
        assistant="#B48EAD",
        tool_read="#81A1C1",
        tool_write="#A3BE8C",
        tool_delete="#BF616A",
        tool_shell="#EBCB8B",
        diff_add="#A3BE8C",
        diff_remove="#BF616A",
        diff_context="#4C566A",
        border_primary="#88C0D0",
        border_secondary="#81A1C1",
        border_success="#A3BE8C",
        border_warning="#EBCB8B",
        border_error="#BF616A",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Monokai Pro - Classic code editor theme
    # ───────────────────────────────────────────────────────────────────────────
    "monokai": Theme(
        name="Monokai Pro",
        primary="#66D9EF",       # Cyan
        secondary="#AE81FF",     # Purple
        accent="#F92672",        # Pink
        success="#A6E22E",       # Green
        warning="#E6DB74",       # Yellow
        error="#F92672",         # Pink/Red
        info="#66D9EF",          # Cyan
        dim="#75715E",           # Comment
        muted="#F8F8F2",         # White
        background="#272822",    # Background
        foreground="#F8F8F2",    # White
        prompt="#66D9EF",
        assistant="#AE81FF",
        tool_read="#66D9EF",
        tool_write="#A6E22E",
        tool_delete="#F92672",
        tool_shell="#E6DB74",
        diff_add="#A6E22E",
        diff_remove="#F92672",
        diff_context="#75715E",
        border_primary="#66D9EF",
        border_secondary="#AE81FF",
        border_success="#A6E22E",
        border_warning="#E6DB74",
        border_error="#F92672",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Tokyo Night - Elegant dark theme
    # ───────────────────────────────────────────────────────────────────────────
    "tokyo": Theme(
        name="Tokyo Night",
        primary="#7AA2F7",       # Blue
        secondary="#BB9AF7",     # Purple
        accent="#F7768E",        # Red
        success="#9ECE6A",       # Green
        warning="#E0AF68",       # Yellow
        error="#F7768E",         # Red
        info="#7DCFFF",          # Cyan
        dim="#565F89",           # Comment
        muted="#A9B1D6",         # Foreground dim
        background="#1A1B26",    # Background
        foreground="#C0CAF5",    # Foreground
        prompt="#7AA2F7",
        assistant="#BB9AF7",
        tool_read="#7DCFFF",
        tool_write="#9ECE6A",
        tool_delete="#F7768E",
        tool_shell="#E0AF68",
        diff_add="#9ECE6A",
        diff_remove="#F7768E",
        diff_context="#565F89",
        border_primary="#7AA2F7",
        border_secondary="#BB9AF7",
        border_success="#9ECE6A",
        border_warning="#E0AF68",
        border_error="#F7768E",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Catppuccin Mocha - Soothing pastel theme
    # ───────────────────────────────────────────────────────────────────────────
    "catppuccin": Theme(
        name="Catppuccin Mocha",
        primary="#89B4FA",       # Blue
        secondary="#CBA6F7",     # Mauve
        accent="#F5C2E7",        # Pink
        success="#A6E3A1",       # Green
        warning="#F9E2AF",       # Yellow
        error="#F38BA8",         # Red
        info="#89DCEB",          # Sky
        dim="#6C7086",           # Overlay0
        muted="#BAC2DE",         # Subtext1
        background="#1E1E2E",    # Base
        foreground="#CDD6F4",    # Text
        prompt="#89B4FA",
        assistant="#CBA6F7",
        tool_read="#89DCEB",
        tool_write="#A6E3A1",
        tool_delete="#F38BA8",
        tool_shell="#F9E2AF",
        diff_add="#A6E3A1",
        diff_remove="#F38BA8",
        diff_context="#6C7086",
        border_primary="#89B4FA",
        border_secondary="#CBA6F7",
        border_success="#A6E3A1",
        border_warning="#F9E2AF",
        border_error="#F38BA8",
    ),

    # ───────────────────────────────────────────────────────────────────────────
    # Minimal Light - Clean light theme
    # ───────────────────────────────────────────────────────────────────────────
    "light": Theme(
        name="Minimal Light",
        primary="#0969DA",       # Blue
        secondary="#8250DF",     # Purple
        accent="#CF222E",        # Red
        success="#1A7F37",       # Green
        warning="#9A6700",       # Yellow/Brown
        error="#CF222E",         # Red
        info="#0969DA",          # Blue
        dim="#656D76",           # Gray
        muted="#1F2328",         # Dark text
        background="#FFFFFF",    # White
        foreground="#1F2328",    # Dark text
        prompt="#0969DA",
        assistant="#8250DF",
        tool_read="#0969DA",
        tool_write="#1A7F37",
        tool_delete="#CF222E",
        tool_shell="#9A6700",
        diff_add="#1A7F37",
        diff_remove="#CF222E",
        diff_context="#656D76",
        border_primary="#0969DA",
        border_secondary="#8250DF",
        border_success="#1A7F37",
        border_warning="#9A6700",
        border_error="#CF222E",
    ),
}


# Default theme
DEFAULT_THEME = "deepseek"

# Current active theme (module-level state)
_current_theme: Theme = THEMES[DEFAULT_THEME]


def get_theme(name: Optional[str] = None) -> Theme:
    """Get a theme by name, or return the current theme."""
    if name is None:
        return _current_theme
    return THEMES.get(name.lower(), THEMES[DEFAULT_THEME])


def set_theme(name: str) -> Theme:
    """Set the active theme."""
    global _current_theme
    _current_theme = get_theme(name)
    return _current_theme


def list_themes() -> list[str]:
    """List all available theme names."""
    return list(THEMES.keys())


def create_custom_theme(
    name: str,
    base: str = DEFAULT_THEME,
    **overrides: str,
) -> Theme:
    """Create a custom theme based on an existing one with overrides."""
    base_theme = THEMES.get(base, THEMES[DEFAULT_THEME])

    # Get all fields from base theme
    theme_dict = {
        field: getattr(base_theme, field)
        for field in Theme.__dataclass_fields__
    }

    # Apply overrides
    theme_dict["name"] = name
    for key, value in overrides.items():
        if key in theme_dict:
            theme_dict[key] = value

    return Theme(**theme_dict)
