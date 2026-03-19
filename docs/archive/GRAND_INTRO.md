# 🌟 Grand Introduction & Interactive Themes

## 1. Grand Startup Screen
Every time you start (or run `/intro`), you'll see a stunning ASCII art banner:

```
      ██████╗ ███████╗███████╗██████╗ ███████╗███████╗██╗  ██╗
      ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝██║ ██╔╝
      ██║  ██║█████╗  █████╗  ██████╔╝███████╗█████╗  █████╔╝
      ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝ ╚════██║██╔══╝  ██╔═██╗
      ██████╔╝███████╗███████╗██║     ███████║███████╗██║  ██╗
      ╚═════╝ ╚══════╝╚══════╝╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝
             DeepSeek Code - Intelligent Terminal Agent

          Working in: /Users/mansur/deepseek code
           Model: deepseek-chat (standard)
     Type /intro for setup or /help for commands.
```

## 2. Interactive Theme Selector
Just like Claude Code, you can now interactively choose your theme with a live preview!

Run `/theme` or `/intro`:

```
  Choose the text style that looks best with your terminal
  To change this later, run /theme

 ❯ 1. DeepSeek (Default) ✔
   2. Dracula
   3. Nord
   4. Tokyo Night
   5. GitHub Dark
   6. Monokai Pro

  ↑/↓: Navigate  Enter: Select  Esc: Cancel

  Preview: DeepSeek
  ────────────────────────────────────────

    def greet(name: str):
        print(f"Hello, {name}!")
        return True

  ────────────────────────────────────────
```

## 3. Improvements
- **Startup:** Replaced simple banner with ASCII art
- **Commands:** Added `/intro` and `/theme`
- **UX:** Interactive menus for configuration

---

## 🚀 Try It
```bash
> /intro
```
*(Shows banner + theme selector)*

```bash
> /theme
```
*(Shows theme selector only)*
