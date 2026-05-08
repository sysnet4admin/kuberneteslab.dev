---
title: "cc-deck: Claude Code Session Browser and Task Manager"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh"]
categories: ["Tools"]
description: "When you work across multiple projects with Claude Code, it gets hard to track where you left off. cc-deck is a zsh function that opens an fzf TUI showing all your past sessions with the last thing you typed as a preview — with TODOs pinned at the top."
summary: "A zsh function that browses Claude Code sessions via fzf TUI, auto-pins memory TODOs, and resumes the right session in the right directory."
ShowToc: true
TocOpen: true
---

## The Problem

Claude Code already shows a resume link when you type `/quit`. But if your terminal crashes, or you just want to pick up a session you worked on yesterday, `claude --resume` gives you a compressed list that's hard to parse. You end up spending more time figuring out which session was which than actually working.

The other issue: when you tell Claude to monitor something for a few days — *"watch this and let me know"* — that note sits in memory somewhere, but there's no obvious way to surface it the next time you open a session.

## What cc-deck Does

`cc-deck` is a small zsh function that opens an fzf picker showing your recent Claude Code sessions. Each entry shows the **last thing you typed** in that session, not a compressed summary.

```
[TODO] /tmp/projects/infra/k8s: Watch for OOMKill recurrence over the next 2 weeks
[PIN]  /tmp/projects/api-server: how do we fix it without rolling back?
────────────────────────────────────────────────────────────────────────
* 2026-05-08 09:14  /tmp/projects/api-server:    how do we fix it without rolling back?
  2026-05-08 08:59  /tmp/projects/infra/k8s:    applied — monitor it and let me know if OOMKills again
  2026-05-08 08:38  /tmp/projects/frontend:     what's the fix?
  2026-05-08 08:17  /tmp/projects/auth-service: what about token revocation?
  2026-05-08 07:59  /tmp/projects/monitoring:   also add an error rate alert
```

TODOs from Claude memory are pinned at the top automatically. Select a session and it `cd`s to the right directory before resuming.

![demo](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo.gif)

## Key Features

**Session browser with last-input preview**  
Instead of opaque UUIDs or compressed summaries, cc-deck shows what you were actually asking. The last user input from each session is extracted directly from the JSONL file.

**Auto-pinned TODOs**  
When you say things like *"add this to memory as a TODO"* or *"check this again next week"*, Claude writes a memory file with `type: project` and a name starting with `TODO`. cc-deck detects these automatically and pins them at the top, linked back to the originating session.

**Manual pin with Ctrl-K**  
Any session can be manually pinned or unpinned with `Ctrl-K`. Pinned sessions stay at the top until you remove them.

**Smart resume**  
Selecting a session automatically runs `cd` to the original directory before calling `claude --resume`. No manual navigation needed.

**4 resume modes**  
Switch between `claude`, `claude-api`, `--dangerously-skip-permissions`, and combinations using `Ctrl-O/A/D/X`. The last selected mode is remembered across runs.

**Fast**  
An mtime-based cache keeps repeat runs at ~0.04 seconds for 100 sessions.

## Installation

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

Requires [fzf](https://github.com/junegunn/fzf): `brew install fzf`

## How TODOs Get Pinned

When you ask Claude to track something:

```
add this to memory as a TODO
check back on this next week
keep an eye on this for a few days
```

Claude writes a memory file like this:

```yaml
---
name: TODO - Monitor EKS cluster after 3Gi memory limit applied
description: Watch for OOMKill recurrence over the next 2 weeks
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck scans `~/.claude/projects/*/memory/*.md` for entries with `type: project` and a name starting with `TODO`, then links them to the original session via `originSessionId`. No extra setup needed.

## Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Resume with last saved mode |
| `Ctrl-K` | Pin / unpin current session |
| `Ctrl-O` | Resume with `claude` |
| `Ctrl-A` | Resume with `claude-api` |
| `Ctrl-D` | Resume with `claude --dangerously-skip-permissions` |
| `Ctrl-X` | Resume with `claude-api --dangerously-skip-permissions` |

## Source

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
