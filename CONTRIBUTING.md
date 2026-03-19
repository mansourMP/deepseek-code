# Contributing to DS Code Agent

Thank you for your interest in contributing to DS Code Agent. We welcome community contributions to improve this independent terminal coding agent.

## How to Contribute

1.  **Fork the Repository:** Create a fork of the repository on GitHub.
2.  **Create a Feature Branch:** `git checkout -b feature/your-feature-name`
3.  **Set up Development Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    ```
4.  **Make Your Changes:** Implement your feature or fix. Ensure your code follows the existing style and is well-documented.
5.  **Run Quality Checks:**
    ```bash
    pytest
    ruff check src/
    ruff format src/
    mypy src/
    ```
6.  **Add Tests:** If you're adding a new feature, please include corresponding tests.
7.  **Submit a Pull Request:** Open a PR against the `main` branch with a clear description of your changes.

## Code Style

- We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.
- We use [Mypy](https://github.com/python/mypy) for static type checking.
- Please follow PEP 8 and use clear, descriptive variable and function names.

## Reporting Issues

- Use the GitHub Issues tracker to report bugs or suggest features.
- Provide as much detail as possible, including steps to reproduce bugs and examples for new features.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
