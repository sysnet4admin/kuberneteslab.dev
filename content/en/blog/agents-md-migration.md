---
title: "Does switching CLAUDE.md to AGENTS.md slow Claude Code down?"
date: 2026-07-03
draft: false
tags: ["claude-code", "agents-md", "aaif", "context-file", "llm-agent", "benchmark", "kubernetes"]
categories: ["AI"]
description: "Measured whether the two workarounds for migrating a project context file from CLAUDE.md to AGENTS.md (import and symlink) cost speed or tokens in Claude Code, across 4 model tiers and 174 runs. No penalty on either axis."
summary: "The two AGENTS.md migration workarounds (import, symlink) were measured on Kubernetes incident-response tasks: no penalty in speed or context-load tokens, and the import even came in 3 to 4% lighter."
ShowToc: true
TocOpen: true
---

## The context files keep multiplying

If your team uses AI coding agents, your repository root probably collects files like these: a `CLAUDE.md` for Claude Code, a rules file for Cursor, instructions for Copilot. The content is nearly identical: build commands, test procedures, boundaries the agent must not cross. Every new tool means copying the same content under another filename, and fixing one copy means forgetting another.

[AGENTS.md](https://agents.md/) is the industry's answer: an open format governed by AAIF (Agentic AI Foundation) under the Linux Foundation, read by 30+ agents. One file to cover every tool.

But Claude Code does not read AGENTS.md natively yet ([issue #34235](https://github.com/anthropics/claude-code/issues/34235)). Migrating requires a workaround: either keep a single `@AGENTS.md` import line in `CLAUDE.md`, or turn `CLAUDE.md` into a symlink pointing at `AGENTS.md`.

That is where the worry starts. A context file loads on every agent session, so even a small cost in the indirection compounds across every session your team runs. Princeton's [measurement study](https://arxiv.org/abs/2601.20404) covered only Codex, which reads AGENTS.md natively; nobody had measured the import or symlink path. So I measured it. The numbers and the reproduction steps are in the [GitHub repository](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration).

## What was measured

The same content, delivered three ways:

- **A (native)**: the body lives in `CLAUDE.md`, as today.
- **B (import)**: `CLAUDE.md` holds a single `@AGENTS.md` line; the body moves to `AGENTS.md`.
- **C (symlink)**: the body lives in `AGENTS.md`; `CLAUDE.md` is a symlink to it.

The payload is checksum-identical across the three conditions, and it is not a synthetic document: it is the working context file of a real benchmark project (cluster rules, scoring formulas, known pitfalls).

The tasks are Kubernetes incident response. On a dedicated cluster, each run injects a fault (a broken deployment, a wrong Service selector, an OOM limit) and the agent has to find and fix it. Before measuring speed, a canary line planted in the payload ("answer PING with PONG") confirmed each delivery method actually loads: all three responded, and a no-context control did not, so the check itself is valid.

The volume: one pass over 10 scenarios (30 runs, Sonnet), then a sweep over the 4 low-variance scenarios with 4 models (Haiku 4.5, Sonnet 4.6, Opus 4.8, Fable 5) x 3 repetitions (144 runs). All 174 runs completed cleanly.

## The result: nothing to worry about

The most honest cost signal is the one-time context-load tokens at session start (cache write). If the indirection inflated what gets loaded, B or C would exceed A here. The opposite happened.

| Model | A (native) | B (import) vs A | C (symlink) vs A |
|---|---|---|---|
| Haiku 4.5 | 22,049 | -3% | +1% |
| Sonnet 4.6 | 14,357 | -3% | -1% |
| Opus 4.8 | 15,542 | -4% | -1% |
| Fable 5 | 16,357 | -3% | -1% |

The import (B) comes in 3 to 4% *lower* on all four models. A consistent sign across four tiers is not noise. The symlink (C) sits within ±1% of native, effectively identical.

Wall time swings more, but with no direction: B is faster on some models and slower on others, and the largest time gaps come with near-zero token gaps. A delivery-method overhead would push one way consistently; this pattern is the agent taking a slightly different solution path each run. Per-model numbers are in the [README results section](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration).

## Why it comes out this way

The symlink being free is simple: the moment Claude Code opens the `CLAUDE.md` path, the OS resolves the link and returns the content of `AGENTS.md`. From Claude Code's side the read is identical to native; the filesystem does the work. That matches the measurement exactly (C within ±1% of A).

The import's -3% was the surprise. Same body, fewer load tokens, which suggests Claude Code renders an imported file slightly differently from native inline content. Either way, the point stands: the workaround is not a tax.

## What this means for a team

You can make AGENTS.md the canonical file and shrink `CLAUDE.md` to a single `@AGENTS.md` line. You lose neither speed nor tokens, and however many tools you add, there is one file to maintain.

Two caveats. First, this measurement answers the speed and token-cost question; answer accuracy and safety (whether destructive kubectl commands increase or decrease) need separate scoring and were not part of this pass. Second, what you put in the file matters more than how you deliver it: an [ETH Zurich study](https://arxiv.org/abs/2602.11988) found LLM-generated context files lowered success rates and raised costs by over 20%. Curate the file by hand; pick whichever delivery method is convenient.

## Closing

What blocks a migration is usually an unmeasured worry. "It might be slower" does not go away until someone measures it. Measured, there was no penalty on any tier from Haiku to Fable, and the import even came in slightly lighter. The harness, cluster provisioning, and aggregation scripts are all in the [GitHub repository](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration), so you can run the same comparison with your own context file.
