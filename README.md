<p align="center">
  <img src="https://raw.githubusercontent.com/deepseek/deepseek-code/main/.github/logo.svg" alt="DeepSeek Code" width="120">
</p>

<h1 align="center">DeepSeek Code</h1>

<p align="center">
  <strong>A powerful terminal coding agent powered by DeepSeek API</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#themes">Themes</a> •
  <a href="#safety">Safety</a>
</p>

---

## ✨ Features

- 🚀 **Powerful AI Coding** - Leverage DeepSeek's advanced models for code generation, refactoring, and debugging
- 🎨 **Beautiful UI** - 8 stunning themes (DeepSeek, GitHub, Dracula, Nord, Monokai, Tokyo Night, Catppuccin, Light)
- 🔒 **Enterprise-Grade Security** - Comprehensive sandboxing, command denylist, path validation
- 💾 **Undo Support** - Full backup and restore for every file modification
- ⚡ **Streaming Output** - Real-time AI responses with elegant animations
- 🛠️ **Rich Toolset** - File operations, search, shell commands, JSON chunking
- 📊 **Context Management** - Smart token tracking and history trimming
- 🎯 **Multiple Modes** - Safe, Standard, Agent, and Read-only modes

## 📦 Installation

### Using pipx (Recommended)

```bash
pipx install .
```

### Using pip

```bash
pip install .
```

### Development Setup

```bash
git clone https://github.com/deepseek/deepseek-code.git
cd deepseek-code
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 🚀 Quickstart

1. **Set your API key:**

```bash
export DEEPSEEK_API_KEY=sk-xxx
```

2. **Launch DeepSeek Code:**

```bash
deepseek
```

3. **Start coding!**

```
❯ List all TODO comments in this project
❯ Refactor the User class to use dataclasses
❯ Write unit tests for the authentication module
❯ Fix the bug in the payment processing code
```

## 💡 Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/exit` | Exit DeepSeek Code |
| `/clear` | Clear conversation history |
| `/status` | Show session status |
| `/model <name>` | Switch model |
| `/models` | List available models |
| `/mode <mode>` | Set mode (safe\|standard\|agent\|readonly) |
| `/theme <name>` | Change theme |
| `/themes` | List available themes |
| `/tools on\|off` | Toggle tool usage |
| `/approve on\|off` | Toggle auto-approve |
| `/debug on\|off` | Toggle debug mode |
| `/undo` | Undo last file write |
| `/tokens` | Show token usage |
| `/history` | Show recent conversation |

## ⚙️ Configuration

Create `.deepseek-code.json` in your project root:

```json
{
  "theme": "deepseek",
  "mode": "standard",
  "auto_approve": false,
  "approve_reads": false,
  "readonly": false,
  
  "default_model": "deepseek-chat",
  "max_messages": 50,
  "max_context_tokens": 32000,
  
  "stream_word_delay_ms": 0,
  "show_token_usage": true,
  
  "denylist": ["rm -rf", "sudo", "mkfs"]
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `theme` | string | `"deepseek"` | Color theme |
| `mode` | string | `"standard"` | Operating mode |
| `auto_approve` | bool | `false` | Auto-approve file writes |
| `approve_reads` | bool | `false` | Require approval for reads |
| `readonly` | bool | `false` | Block all write operations |
| `default_model` | string | `"deepseek-chat"` | Default AI model |
| `max_messages` | int | `50` | Max conversation messages |
| `max_context_tokens` | int | `32000` | Max context window tokens |
| `denylist` | array | `[]` | Blocked shell command patterns |

## 🎨 Themes

DeepSeek Code includes 8 beautiful themes:

| Theme | Description |
|-------|-------------|
| **deepseek** | Futuristic cyan/purple (default) |
| **github** | GitHub Dark colors |
| **dracula** | Popular Dracula theme |
| **nord** | Arctic, bluish palette |
| **monokai** | Classic Monokai Pro |
| **tokyo** | Elegant Tokyo Night |
| **catppuccin** | Soothing Catppuccin Mocha |
| **light** | Clean light theme |

Switch themes with `/theme <name>` or set in config:

```json
{
  "theme": "dracula"
}
```

### Custom Themes

Override any color in your config:

```json
{
  "theme": "deepseek",
  "custom_theme": {
    "primary": "#FF6B6B",
    "success": "#4ECDC4"
  }
}
```

## 🔒 Safety

DeepSeek Code includes comprehensive security features:

### Sandboxing
- All file operations are sandboxed to the project root
- Path traversal attacks are blocked
- Symlink escapes are prevented

### Command Denylist
Built-in protection against dangerous commands:
- `rm -rf`, `sudo`, `dd`, `mkfs`
- Fork bombs
- Privilege escalation
- Network exfiltration

### Sensitive Files
Automatic protection for:
- `.env` files
- Private keys (`.pem`, `.key`)
- SSH keys
- AWS credentials

### Operating Modes

| Mode | Tools | Auto-Approve | Writes |
|------|-------|--------------|--------|
| **safe** | ❌ | ❌ | ❌ |
| **standard** | ✅ | ❌ | ✅ (with approval) |
| **agent** | ✅ | ✅ | ✅ |
| **readonly** | ✅ | ❌ | ❌ |

## 🛠️ Tools

The agent has access to:

| Tool | Description |
|------|-------------|
| `list_dir` | List directory contents |
| `read_file` | Read file contents (up to 10MB) |
| `write_file` | Write file (approval required) |
| `delete_file` | Delete file (approval required) |
| `search` | Search with regex patterns |
| `run_shell` | Run shell commands (approval required) |
| `read_json_chunk` | Read slice of large JSON file |
| `write_json_chunk` | Write slice of large JSON file |

## 📊 Chunk Mode

For processing large JSON files that exceed context limits:

```bash
deepseek --file "data/large.json" --start 0 --count 50 --state ".state.json"
```

This enables:
- Processing in manageable chunks
- Resume support via state file
- Targeted edits without loading entire file

## 🔧 CLI Options

```bash
deepseek [OPTIONS]

Options:
  --model TEXT              Model name (default: deepseek-chat)
  --debug                   Enable debug logging
  --log                     Write conversation log
  --auto-approve           Auto-approve all operations
  --word-delay INT         Streaming delay per word (ms)
  --max-context INT        Max context tokens
  --timestamps/--no-timestamps  Show timestamps
  --mode [safe|standard|agent|readonly]  Operating mode
  --approve-reads          Require approval for reads
  --file TEXT              JSON file for chunk mode
  --start INT              Chunk start index
  --count INT              Chunk count
  --state TEXT             State file for resume
  --version                Show version
  --help                   Show help
```

## 🧪 Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=deepseek_code --cov-report=html

# Specific test file
pytest tests/test_comprehensive.py -v
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
ruff format src/
```

## 📁 Project Structure

```
deepseek-code/
├── src/deepseek_code/
│   ├── __init__.py
│   ├── cli.py           # Main CLI entry point
│   ├── agent.py         # DeepSeek API agent
│   ├── tools.py         # Tool implementations
│   ├── config.py        # Configuration management
│   ├── safety.py        # Security & sandboxing
│   ├── session.py       # Session state & backups
│   ├── tokens.py        # Token counting
│   ├── logging_utils.py # Conversation logging
│   └── ui/
│       ├── themes.py    # Color themes
│       ├── panels.py    # Rich panel components
│       ├── animations.py # Loading states
│       ├── approval.py  # Approval workflows
│       └── commands.py  # Slash commands
├── tests/
│   └── test_comprehensive.py
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by the DeepSeek team
</p>
