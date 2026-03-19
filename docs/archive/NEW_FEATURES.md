# ✅ New Features: Plan Mode & Interactive UI

## 1. Plan Mode 📋
A new read-only mode for exploration and planning.

```bash
❯ /mode plan
✓ Plan mode enabled
Agent will explore in read-only mode and create plans

❯ add user auth
📋 PLAN:
1. Create user model...
```

## 2. Interactive Approvals 🛡️
Beautiful interactive selector for approval modes (Codex-style).

```bash
❯ /approvals

  Select Approval Mode

    1. Safe (Read Only)
  › 2. Standard (Manual Approval)
    3. Plan Mode
    4. Agent (Auto-Approve)
    5. Read Only

  ↑/↓: Navigate  Enter: Select
```

## 3. Beautiful Status 📊
New `/status` command visualizes your session.

```
 DeepSeek Code (v0.2.0)
 
 Model:            deepseek-chat
 Directory:        /Users/mansur/deepseek code
 Approval:         On-Request
 Sandbox:          Standard
 Mode:             Plan
 Session:          019bc154-2ca1...
 
 Context window:   57% left (119K used / 258K)
 5h limit:         [███████████████████░] 97% left (mock)
 Weekly limit:     [███████░░░░░░░░░░░░░] 33% left (mock)
```

## 4. Command Menu ⌨️
Type `/` or `/help` to see the command menu.

```
Command               Description
/approvals            Choose approval mode interactively
/clear                Clear conversation
/debug                Toggle debug (/debug on|off)
/exit                 Exit
/help                 Show commands
/history              Show recent conversation
/mode                 Set mode (/mode safe|standard|agent|plan|readonly)
/model                Change model (interactive or by name)
/new                  Start a new chat session
/status               Show session status
...
```

## 5. New Session 🆕
Type `/new` to start fresh without restarting the app.

```bash
❯ /new
✓ Started new session
```

---

## 🚀 Try It Now

1. **Plan Mode:** `/mode plan`
2. **Approval Selector:** `/approvals`
3. **Session Status:** `/status`
4. **New Session:** `/new`
5. **Command Menu:** Type `/`
