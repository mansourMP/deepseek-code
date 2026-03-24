# DeepSeek Code (DS-Code)

> **The High-Performance Engineering CLI for DeepSeek Models.**
> *Independent open-source project. Not affiliated with DeepSeek-AI.*

---

### ⚠️ Project Status Notice

This project is currently in a **maintenance-only state**. 

While the core functionality is robust, full-scale engine engineering reached its limits as further optimization requires deep internal architectural access to DeepSeek's proprietary infrastructure. Consequently, active development has been paused.

**Free to Use & Open to Feedback:**
- This tool remains **free to use** and open-source.
- If you find it useful, encounter errors, or have recommendations for improvements, please **open an issue** or submit a pull request!

---

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://www.python.org/downloads/)
[![Unofficial](https://img.shields.io/badge/Project-Unofficial-orange.svg)](https://github.com/mansourMP/deepseek-code)

**DeepSeek Code** is a professional terminal-based coding assistant optimized for high-performance engineering workflows. It provides an autonomous, Codex-style environment for building, refactoring, and exploring complex codebases.

---

## ✨ Capabilities

- **Autonomous Engineering:** A ReAct-based agent that orchestrates multi-file tasks, runs tests, and navigates directories.
- **Professional TUI:** A persistent, high-density terminal interface with real-time status and context tracking.
- **Local Integrity:** Built-in sandboxing with path validation and safe execution guards.
- **Context Mastery:** Intelligent token management and optimized prompt engineering for DeepSeek-V3 and R1.
- **Tool Integration:** Seamlessly reads, writes, and executes within your local development environment.

## 🚀 Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/mansourMP/deepseek-code.git
cd deepseek-code

# Set up environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### Configuration

Add your credentials to a `.env` file:

```bash
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_MODEL=deepseek-chat
```

### CLI Usage

- `deepseek`: Launch the interactive terminal assistant.
- `deepseek-auto "your goal"`: Run the autonomous orchestrator for complex tasks.
- `ds-code`: Alternative alias for the CLI.

## 🛠 Architecture

```
deepseek-code/
├── src/deepseek_code/
│   ├── cli.py           # CLI Entry point
│   ├── engine.py        # ReAct loop & Tool orchestration
│   ├── agent.py         # LLM Client integration
│   └── ui/              # TUI, Themes, and Animations
├── docs/                # Technical documentation
├── tests/               # Suite of comprehensive tests
└── pyproject.toml       # Build & Dependency configuration
```

## 🤝 Contributing

We welcome contributions! Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built for engineers, by the open-source community.
</p>
