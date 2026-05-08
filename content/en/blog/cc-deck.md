---
title: "cc-deck: Claude Code Session Hub"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh"]
categories: ["Tools"]
description: "Claude Code sessions pile up across projects. cc-deck is a zsh function that turns them into a searchable hub — fuzzy search by what you were asking, auto-pin TODOs from Claude memory, bookmark sessions with Ctrl-K, and resume in the right directory."
summary: "A zsh function that makes Claude Code sessions searchable and manageable — fuzzy search, TODO auto-pinning, manual bookmarks, and smart resume."
ShowToc: true
TocOpen: true
---

## The Problem

Claude Code sessions pile up across projects. When you need to get back to something — yesterday's debugging session, a task Claude flagged for follow-up, or a session you want to bookmark — finding it and resuming in the right context takes friction.

`claude --resume` shows a list, but the summaries are compressed and hard to read. You end up scrolling through UUIDs instead of working.

## What cc-deck Does

`cc-deck` opens an fzf TUI over all your Claude Code sessions. Each entry shows the **last thing you typed**, not a summary. Type anything to filter in real time. TODOs from Claude memory and manually pinned sessions are always at the top.

![demo](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_social.gif)

## Features

### 1. Fuzzy Search

Type anything in the prompt to filter sessions by last input content in real time.

```
cc-deck> OOM
  2/100
  2026-05-08 08:59  /tmp/projects/infra/k8s: pod keeps OOMKilling after we scaled up
```

No need to remember when or where a session happened — search by what you were actually working on.

---

### 2. Auto-pinned TODOs

When you ask Claude to track something for later:

```
add this to memory as a TODO
check back on this next week
keep an eye on this for a few days
```

Claude writes a memory entry like this:

```yaml
---
name: TODO - Monitor EKS cluster after 3Gi memory limit applied
description: Watch for OOMKill recurrence over the next 2 weeks
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck scans `~/.claude/projects/*/memory/*.md` for `type: project` entries with `TODO` in the name, and pins them at the top automatically — linked back to the originating session via `originSessionId`.

```
[TODO] /tmp/projects/infra/k8s: Watch for OOMKill recurrence over the next 2 weeks
```

**Marking a TODO as done:** Press `Ctrl-D` on a TODO entry. cc-deck updates the memory file name from `TODO - Monitor EKS ...` to `Monitor EKS ... (completed)`. The entry disappears from the list, but the memory file is preserved so Claude still has the context.

---

### 3. Manual PIN

Bookmark any session you want to return to quickly. Navigate to a session and press `Ctrl-K`. The session's last input is saved as the label and it appears at the top of the list.

```
[PIN]  /tmp/projects/api-server: memory usage keeps climbing after the last deploy
```

Press `Ctrl-K` again on a pinned entry to remove it.

---

### 4. Smart Resume

Select any entry — TODO, PIN, or regular session — and cc-deck automatically:
1. `cd`s to the original working directory
2. Calls `claude --resume <session-id>`

No manual navigation needed.

---

### 5. Resume Modes

Four modes available via keyboard shortcuts. The last selected mode is remembered across runs.

| Key | Command |
|-----|---------|
| `Enter` | Last saved mode |
| `Ctrl-O` | `claude` |
| `Ctrl-A` | `claude-api` |
| `Ctrl-S` | `claude --dangerously-skip-permissions` |
| `Ctrl-X` | `claude-api --dangerously-skip-permissions` |

Override the default with an env var:

```zsh
export CLAUDE_DECK_CMD="claude-api"
```

---

### 6. Performance

An mtime-based cache keeps repeat runs at ~0.04s for 100 sessions.

## Installation

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

Requires [fzf](https://github.com/junegunn/fzf): `brew install fzf`

## All Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Resume with last saved mode |
| `Ctrl-K` | Pin / unpin current session |
| `Ctrl-D` | Mark TODO as done / remove PIN |
| `Ctrl-O` | Resume with `claude` |
| `Ctrl-A` | Resume with `claude-api` |
| `Ctrl-S` | Resume with `claude --dangerously-skip-permissions` |
| `Ctrl-X` | Resume with `claude-api --dangerously-skip-permissions` |
| `ESC` | Quit |

## Source

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
