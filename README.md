# DS Code Agent (Unofficial)

> **Disclaimer:** This is an independent open-source project and is not affiliated with, endorsed by, or sponsored by DeepSeek-AI. References to DeepSeek refer only to compatibility, inspiration, or intended model usage.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://www.python.org/downloads/)
[![Unofficial](https://img.shields.io/badge/Project-Unofficial-orange.svg)](https://github.com/your-username/ds-code-agent)

**DS Code Agent** is an independent, terminal-based coding assistant designed for use with DeepSeek-compatible models. It provides a professional, Codex-like environment optimized for high-performance AI coding workflows.

---

## ✨ Features

- **Autonomous Agent:** A ReAct-based coding engine that can explore directories, read/write files, and run shell commands.
- **Advanced TUI:** A persistent, pinned bottom prompt with real-time status (Codex-style).
- **Safe Sandboxing:** Comprehensive path validation and command denylists to protect your local environment.
- **Multi-Step Orchestration:** A dedicated autonomous mode for complex, multi-file engineering tasks.
- **Context Optimization:** Intelligent token management and real-time usage tracking.

## 🚀 Installation & Usage

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/ds-code-agent.git
cd ds-code-agent

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

### Quick Commands

- `deepseek`: Launch the interactive terminal assistant.
- `deepseek-auto "goal"`: Run the autonomous orchestrator for multi-step goals.
- `/help`: Show all available commands in the interactive session.

## 🛠 Project Structure

```
ds-code-agent/
├── src/deepseek_code/
│   ├── cli.py           # CLI entry point
│   ├── engine.py        # ReAct loop & tool orchestration
│   ├── agent.py         # Model API client
│   └── ui/              # TUI components & themes
├── docs/                # Documentation & archive
├── tests/               # Comprehensive test suite
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. This project is maintained by the open-source community.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built by independent developers
</p>
