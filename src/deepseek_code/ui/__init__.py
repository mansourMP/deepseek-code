"""UI components for DeepSeek Code terminal interface."""

from .animations import (
    DEEP_THINKING_MESSAGES,
    THINKING_MESSAGES,
    PulseText,
    StatusRotator,
    ToolExecutionSpinner,
    print_typing,
    show_error,
    show_info,
    show_success,
    show_thinking,
    show_warning,
)
from .approval import (
    InteractiveMenu,
    confirm_action,
    confirm_write,
)
from .commands import (
    COMMANDS,
    CommandContext,
    CommandResult,
    dispatch_command,
    get_command_completions,
)
from .panels import (
    diff_preview,
    diff_summary,
    get_tool_description,
    print_approval_prompt,
    print_diff_panel,
    print_shell_panel,
    print_status_panel,
    print_welcome_banner,
)
from .themes import (
    THEMES,
    Theme,
    create_custom_theme,
    get_theme,
    list_themes,
    set_theme,
)

__all__ = [
    # Themes
    "Theme",
    "THEMES",
    "get_theme",
    "set_theme",
    "list_themes",
    "create_custom_theme",
    # Panels
    "diff_preview",
    "diff_summary",
    "print_diff_panel",
    "print_shell_panel",
    "print_status_panel",
    "print_welcome_banner",
    "print_approval_prompt",
    "get_tool_description",
    # Animations
    "StatusRotator",
    "show_thinking",
    "ToolExecutionSpinner",
    "PulseText",
    "print_typing",
    "show_success",
    "show_error",
    "show_warning",
    "show_info",
    "THINKING_MESSAGES",
    "DEEP_THINKING_MESSAGES",
    # Approval
    "confirm_action",
    "confirm_write",
    "InteractiveMenu",
    # Commands
    "COMMANDS",
    "CommandContext",
    "CommandResult",
    "dispatch_command",
    "get_command_completions",
]

