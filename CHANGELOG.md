# Changelog

All notable changes to DS Code Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-15

### Added

#### 🎨 Premium Theme System
- 8 beautiful built-in themes: DeepSeek, GitHub, Dracula, Nord, Monokai, Tokyo Night, Catppuccin, Light
- Custom theme support via config file
- `/theme` and `/themes` commands for runtime theme switching
- Theme-aware UI components throughout

#### 🔒 Enhanced Security
- Comprehensive sandboxing with symlink protection
- Command injection detection and prevention
- Sensitive file pattern blocking (.env, .pem, .key, credentials)
- Blocked directories list (node_modules, .git, etc.)
- Multiple exception types for better error handling

#### 📦 Modular Architecture
- New `ui/` module with separated components:
  - `themes.py` - Theme definitions and management
  - `panels.py` - Rich panel components (diff viewer, shell output)
  - `animations.py` - Loading states and visual feedback
  - `approval.py` - Approval workflow handlers
  - `commands.py` - Slash command system
- `session.py` - Session state, backup manager, persistence
- Enhanced `config.py` with 30+ configuration options

#### 🛠️ New Features
- **Backup Manager**: Full undo support with timestamped backups
- **Session Persistence**: Resume sessions across restarts
- **Chunk State Manager**: Better resume support for large files
- **Token Usage Display**: `/tokens` command shows context usage
- **Mode Cycling**: Seamless switching between safe/standard/agent/readonly

#### 📊 Comprehensive Test Suite
- 42 tests covering all new modules
- Safety tests for sandboxing and command validation
- Configuration roundtrip tests
- Theme system tests
- Command dispatch tests
- Integration workflow tests

### Changed
- Bumped version to 0.2.0
- Improved error messages with more context
- Cleaner default display (separator off by default)
- Better path resolution for macOS symlinks
- Enhanced diff panel with line numbers and color coding

### Fixed
- Path resolution issues with symlinked directories
- Backup paths now properly resolved

## [0.1.1] - 2025-11-20

### Added
- `deepseek` CLI alias alongside `deepseek-code`
- Dots3 spinner for thinking indicator

## [0.1.0] - 2025-11-15

### Added
- Initial MVP release
- Core agent with tool calling
- File operations (read, write, delete)
- Shell command execution with approval
- Directory listing and search
- Context window management
- Configuration via `.deepseek-code.json`
- Safe/Standard/Agent/Readonly modes
- Smooth word-by-word streaming
- Diff preview with approval workflow
- Backup creation for file writes

---

[0.2.0]: https://github.com/mansourMP/deepseek-code/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/mansourMP/deepseek-code/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/mansourMP/deepseek-code/releases/tag/v0.1.0
