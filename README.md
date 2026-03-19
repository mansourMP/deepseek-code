# DS Code Agent

> **Disclaimer:** This is an independent open-source project and is not affiliated with, endorsed by, or sponsored by DeepSeek-AI. References to DeepSeek refer only to compatibility, inspiration, or intended model usage.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**DS Code Agent** is an independent, terminal-based AI coding assistant designed to work with DeepSeek-compatible models. It provides a professional, Codex-like experience directly in your terminal for users who prefer DeepSeek API models.

---

## ✨ Features

- **Autonomous Coding:** A ReAct-based agent that can explore files, write code, and run shell commands.
- **Advanced TUI:** A persistent, pinned bottom prompt with real-time status (Codex-style).
- **Safe Sandboxing:** Comprehensive path validation and command denylists to protect your workspace.
- **Multi-Step Orchestration:** A dedicated autonomous mode for complex, multi-file tasks.
- **Themeable Interface:** Multiple professional color themes including Dracula, Nord, and GitHub Dark.
- **Token Optimization:** Intelligent context management and real-time usage tracking.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/mansourMP/deepseek-code.git
cd deepseek-code

# Set up a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### Configuration

Create a `.env` file in the project root:

```bash
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_MODEL=deepseek-chat
```

### Usage

**Interactive Mode:**
```bash
ds-code-agent
```

**Autonomous Mode:**
```bash
ds-code-agent-auto "refactor the auth logic to use JWT"
```

## 🛠 Project Structure

```
deepseek-code/
├── src/deepseek_code/
│   ├── cli.py           # Main CLI entry point
│   ├── engine.py        # Core ReAct loop and tool orchestration
│   ├── agent.py         # API-backed coding agent
│   ├── tools.py         # Tool implementations
│   ├── ui/              # User interface components (TUI, themes, panels)
│   └── safety.py        # Security & sandboxing
├── docs/                # Documentation and archive
├── tests/               # Comprehensive test suite
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

Contributions are welcome. This is a community-maintained project for users of DeepSeek-compatible models. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built by the open-source community
</p>
