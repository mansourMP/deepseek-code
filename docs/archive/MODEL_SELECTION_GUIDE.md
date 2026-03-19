# 🎯 New Model Selection Feature - User Guide

## What Changed?

The `/model` and `/models` commands now show a **beautiful interactive table** instead of a plain list!

---

## 🆕 New Features

### 1. `/model` (no arguments)
Shows an interactive table of all available models:

```
Fetching available models...

┌─────────────────────────────────────────────────────────────┐
│                     Available Models                        │
├────┬────────────────────────────┬─────────────────────────┤
│ #  │ Model                      │ Status                  │
├────┼────────────────────────────┼─────────────────────────┤
│ 1  │ deepseek-chat              │ ● current               │
│ 2  │ deepseek-coder             │                         │
│ 3  │ deepseek-reasoner          │                         │
└────┴────────────────────────────┴─────────────────────────┘

Current model: deepseek-chat
To change: /model <name> or /model <number>
```

### 2. `/models`
Same as `/model` - shows the interactive table

### 3. `/model <number>`
Select a model by its number from the table:

```
❯ /model 2

✓ Model set to deepseek-coder
```

### 4. `/model <name>`
Select a model by name (still works):

```
❯ /model deepseek-reasoner

✓ Model set to deepseek-reasoner
```

---

## 📊 Visual Comparison

### Before (Old)
```
❯ /models
  deepseek-chat
  deepseek-coder
  deepseek-reasoner

❯ /model
Usage: /model <name>
```

### After (New)
```
❯ /models
Fetching available models...

┌─────────────────────────────────────────────────────────────┐
│                     Available Models                        │
├────┬────────────────────────────┬─────────────────────────┤
│ #  │ Model                      │ Status                  │
├────┼────────────────────────────┼─────────────────────────┤
│ 1  │ deepseek-chat              │ ● current               │
│ 2  │ deepseek-coder             │                         │
│ 3  │ deepseek-reasoner          │                         │
└────┴────────────────────────────┴─────────────────────────┘

Current model: deepseek-chat
To change: /model <name> or /model <number>

❯ /model
[Same beautiful table as above]

❯ /model 2
✓ Model set to deepseek-coder
```

---

## 🎨 Features

✅ **Numbered List** - Easy selection by number
✅ **Current Model Highlighted** - Green dot (●) shows active model
✅ **Rounded Borders** - Beautiful table design
✅ **Status Column** - Shows which model is active
✅ **Color Coded** - Uses your active theme colors
✅ **Helpful Instructions** - Shows how to select

---

## 💡 Usage Examples

### Scenario 1: Browse Available Models
```bash
❯ /model
# or
❯ /models

# Shows table with all models
```

### Scenario 2: Quick Selection by Number
```bash
❯ /model 2

# Instantly switches to the 2nd model in the list
```

### Scenario 3: Selection by Name
```bash
❯ /model deepseek-reasoner

# Switches to deepseek-reasoner
```

### Scenario 4: Check Current Model
```bash
❯ /model

# Table shows current model with green ● indicator
```

---

## 🔧 How It Works

1. **Fetches Models** - Calls DeepSeek API to get available models
2. **Sorts Alphabetically** - Models are sorted for easy browsing
3. **Numbers Them** - Assigns 1, 2, 3, etc. for quick selection
4. **Highlights Current** - Shows which model is active
5. **Displays Table** - Beautiful rounded border table
6. **Accepts Input** - Number or name selection

---

## ⚡ Benefits

| Benefit | Description |
|---------|-------------|
| **Faster** | Select by number instead of typing full name |
| **Clearer** | Table format is easier to scan |
| **Prettier** | Rounded borders and colors |
| **Informative** | Shows current model at a glance |
| **Consistent** | Matches the premium UI design |

---

## 🐛 Troubleshooting

### "No models found"
- Check your `DEEPSEEK_API_KEY` is set correctly
- Verify internet connection
- API might be temporarily unavailable

### "Invalid model number"
- Make sure you're using a number from the table (1, 2, 3, etc.)
- The number must be within the range shown

### Table not showing
- Make sure you've reinstalled: `pip install -e .`
- Check you're using the latest version
- Try running `deepseek` again

---

## 🎯 What You Can Do Now

Instead of this old workflow:
```bash
❯ /models                    # See plain list
  deepseek-chat
  deepseek-coder
  deepseek-reasoner

❯ /model deepseek-coder      # Type full name
```

You can now do this:
```bash
❯ /model                     # See beautiful table
┌────┬────────────────┬──────────┐
│ #  │ Model          │ Status   │
├────┼────────────────┼──────────┤
│ 1  │ deepseek-chat  │ ● current│
│ 2  │ deepseek-coder │          │
│ 3  │ deepseek-reasoner │       │
└────┴────────────────┴──────────┘

❯ /model 2                   # Just type the number!
✓ Model set to deepseek-coder
```

**Much faster and more beautiful!** ✨

---

## 📝 Summary

The new model selection feature gives you:
- ✅ Interactive table view
- ✅ Numbered selection (1, 2, 3...)
- ✅ Name selection (still works)
- ✅ Current model highlighting
- ✅ Beautiful rounded borders
- ✅ Theme-aware colors
- ✅ Helpful instructions

**This is the premium experience you deserve!** 🎉
