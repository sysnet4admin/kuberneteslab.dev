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

`cc-deck` opens an fzf TUI over all your Claude Code sessions. Each entry shows the **last thing you typed**, not a summary. Type anything to filter in real time. TODOs from Claude memory are pinned at the top automatically.

![demo](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_social.gif)

## Key Features

**Fuzzy search**  
Type to filter sessions by last input content. Find any session instantly without remembering when or where it happened.

**Auto-pinned TODOs**  
When you ask Claude to track something — *"add this as a TODO"*, *"check back next week"* — Claude writes a memory entry with `name: TODO ...`. cc-deck detects these automatically and pins them at the top, linked back to the originating session.

**Mark TODO as done with Ctrl-D**  
When a TODO is resolved, press `Ctrl-D`. cc-deck removes `TODO` from the memory entry name and appends `(completed)`. The memory file is preserved so Claude still has the context.

**Manual bookmark with Ctrl-K**  
Pin any session with `Ctrl-K`. The session's last input is saved as the label. Press again to unpin.

**Smart resume**  
Selecting a session automatically `cd`s to the original directory before calling `claude --resume`. No manual navigation needed.

**4 resume modes**  
Switch between `claude`, `claude-api`, `--dangerously-skip-permissions`, and combinations with `Ctrl-O/A/S/X`. The last selected mode is remembered across runs.

**Fast**  
mtime-based cache keeps repeat runs at ~0.04s.

## Installation

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

Requires [fzf](https://github.com/junegunn/fzf): `brew install fzf`

## How TODOs Work

Ask Claude to track something:

```
add this to memory as a TODO
check back on this next week
```

Claude writes a memory file:

```yaml
---
name: TODO - Monitor EKS cluster after 3Gi memory limit applied
description: Watch for OOMKill recurrence over the next 2 weeks
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck scans `~/.claude/projects/*/memory/*.md` for `type: project` entries with `TODO` in the name, and links them to the original session via `originSessionId`. When you press `Ctrl-D` on a TODO, the name becomes `Monitor EKS cluster after 3Gi memory limit applied (completed)` — removed from the list, but the memory is intact.

## Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Resume with last saved mode |
| `Ctrl-K` | Pin / unpin current session |
| `Ctrl-D` | Mark TODO as done / remove PIN |
| `Ctrl-O` | Resume with `claude` |
| `Ctrl-A` | Resume with `claude-api` |
| `Ctrl-S` | Resume with `claude --dangerously-skip-permissions` |
| `Ctrl-X` | Resume with `claude-api --dangerously-skip-permissions` |

## Source

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
