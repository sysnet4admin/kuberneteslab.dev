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

Working across multiple Claude Code projects means sessions pile up fast. When you need to get back to something — yesterday's debugging session, a task Claude flagged for follow-up, or a session you want to bookmark — finding it and resuming in the right context adds friction.

`claude --resume` shows a list, but the summaries are compressed and hard to read. You end up scrolling through UUIDs instead of working.

## What cc-deck Does

`cc-deck` opens an fzf TUI for all your Claude Code sessions. Each entry shows the **last thing you typed**, not a summary. Type anything to filter in real time. TODOs from Claude memory and manually pinned sessions are always at the top.

![demo](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_social.gif)

## Features

### 1. Fuzzy Search

Type anything in the prompt to filter sessions by last input content in real time. No need to remember when or where a session happened.

```
cc-deck> OOM
  2/100
  2026-05-08 08:59  /tmp/projects/infra/k8s: pod keeps OOMKilling after we scaled up
```

Select one — cc-deck moves to the original directory and resumes the session automatically.

---

### 2. Auto-pinned TODOs

When you ask Claude to track something for later:

```
add this to memory as a TODO
check back on this next week
```

Claude writes a memory entry:

```yaml
---
name: TODO - Monitor EKS cluster after 3Gi memory limit applied
description: Watch for OOMKill recurrence over the next 2 weeks
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck scans `~/.claude/projects/*/memory/*.md` for `type: project` entries with `TODO` in the name, and pins them at the top — linked back to the originating session via `originSessionId`. Select one and you're taken straight back to where the work happened.

```
[TODO] /tmp/projects/infra/k8s: Watch for OOMKill recurrence over the next 2 weeks
```

When the TODO is resolved, press `Ctrl-D`. cc-deck renames the memory entry from `TODO - Monitor EKS ...` to `Monitor EKS ... (completed)` and removes it from the list. The memory file itself is preserved, so Claude still has the full context.

---

### 3. Manual PIN

Bookmark any session you want to return to. Find the session and press `Ctrl-K`. The session's last input is saved as the label and it stays pinned at the top.

```
[PIN]  /tmp/projects/api-server: memory usage keeps climbing after the last deploy
```

Select it and cc-deck takes you back to `/tmp/projects/api-server` and resumes exactly where you left off. Press `Ctrl-K` again on a pinned entry to remove it. `Ctrl-D` also removes a PIN.

---

## Also Built In

**Resume modes**  
Four modes — switch anytime. cc-deck remembers which one you used last.

| Key | Command |
|-----|---------|
| `Enter` | Last saved mode |
| `Ctrl-O` | `claude` |
| `Ctrl-A` | `claude-api` |
| `Ctrl-S` | `claude --dangerously-skip-permissions` |
| `Ctrl-X` | `claude-api --dangerously-skip-permissions` |

Set a persistent default with `export CLAUDE_DECK_CMD="claude-api"`.

**Automatic directory switch**  
Every selection — TODO, PIN, or regular session — runs `cd` to the original working directory before `claude --resume`. You're always in the right directory.

**Cache**  
mtime-based session cache keeps repeat runs at ~0.04s.

---

## Installation

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

Requires [fzf](https://github.com/junegunn/fzf): `brew install fzf`

## Source

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
