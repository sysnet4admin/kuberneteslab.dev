---
title: "Claude Code can now read AGENTS.md directly"
date: 2026-09-22
draft: false
tags: ["claude-code", "agents-md", "aaif", "context-file", "llm-agent", "kubernetes"]
categories: ["AI"]
description: "Claude Code 2.1.277 ships native AGENTS.md support. The default only reads it when no CLAUDE.md exists, CLAUDE.local.md counts for that check, and sessions routed through Bedrock or Vertex do not get the feature at all. Existing imports and symlinks can stay, but one SessionStart hook has to go."
summary: "Native support does not mean the workaround has to go. The documented pitfalls, plus 80 runs from the July extension study, decide what to keep and what to fix."
ShowToc: true
TocOpen: true
---

Back in July I wrote [Does switching CLAUDE.md to AGENTS.md slow Claude Code down?](https://kuberneteslab.dev/en/blog/agents-md-migration/), where Claude Code could not read `AGENTS.md` on its own, so the only way to migrate was a workaround: keep a single `@AGENTS.md` import line in `CLAUDE.md`, or turn `CLAUDE.md` into a symlink pointing at `AGENTS.md`. The worry was that the workaround might add cost to every session, so I measured 210 runs, and the answer was that it does not.

Then in September 2026, Claude Code 2.1.277 shipped native `AGENTS.md` support. So should you now remove the workaround? The short answer is that in most cases you do not have to, and there are situations where keeping it is the safer choice. There is exactly one workaround you do have to remove, and there is one place where the default behaves differently from what the name suggests, which makes it easy to conclude that the feature is not working.

## What changed

![How Claude Code reaches your project instructions](/images/agents-md-native-en.svg)

From 2.1.277 a built-in plugin named `agents-md` handles reading `AGENTS.md`, and you pick which files Claude reads by opening `/config` in a session and setting **Project instructions**. The values are these.

| Value | What Claude Code reads |
|---|---|
| `claude-md-or-agents-md` | The default. Your `CLAUDE.md` or `CLAUDE.local.md` when either is in your working directory or above it, and `AGENTS.md` only when neither is |
| `claude-md-and-agents-md` | Both, with each directory's `CLAUDE.md` first and its `AGENTS.md` after |
| `claude-md` | `CLAUDE.md` only |
| `managed-only` | At launch, only your organization's managed `CLAUDE.md` and auto memory. A subdirectory's `CLAUDE.md` and `.claude/rules/` still load when Claude reads a file there |

If you would rather set it in a file than in `/config`, put it under the built-in plugin's ID in `pluginConfigs` in `~/.claude/settings.json`. Project and local settings files are ignored for this value, so it has to live in your user settings, a `--settings` file, or managed settings.

```json
{
  "pluginConfigs": {
    "agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

## Which files the default reads

The default value, `claude-md-or-agents-md`, is exactly what its name says: one or the other, not both. Claude reads `AGENTS.md` only when there is no `CLAUDE.md` in your working directory or anywhere above it. So if your repository still has a `CLAUDE.md`, native support changes nothing for you and your `AGENTS.md` still goes unread.

Which files count for that check matters, and the documentation draws the line clearly. A `CLAUDE.md`, a `.claude/CLAUDE.md`, or a `CLAUDE.local.md` in your working directory or above it all count. Your user-level `~/.claude/CLAUDE.md`, your organization's managed file, and everything under `.claude/rules/` do not count, and they keep loading alongside `AGENTS.md`.

The `CLAUDE.local.md` entry is the one that bites. Teams that treat `AGENTS.md` as the single source of truth often keep personal, uncommitted instructions in a `CLAUDE.local.md`, and because that file counts, `AGENTS.md` stops loading for the person who created it and for nobody else. Your colleagues on the same repository see it load, your own session does not, and that is an unpleasant thing to debug. To keep the local file and still have `AGENTS.md` read, set Project instructions to `claude-md-and-agents-md`.

It is worth knowing the reading range too. At session start Claude reads every `AGENTS.md` and `.claude/AGENTS.md` in your working directory and the directories above it, and in a subdirectory it reads that directory's `AGENTS.md` when it opens a file there with the Read tool and the subdirectory has none of the three `CLAUDE.md` files of its own.

Some files are never read: `AGENTS.local.md`, `AGENTS.override.md`, and anything under a `.agents/` directory. On the other hand, `@path` imports inside an `AGENTS.md` are expanded as usual, `claudeMdExcludes` patterns apply the same way, and subagents set to skip project instructions skip these files too.

## Sessions that do not get the feature

Shipping the feature does not mean every session has it. The documented conditions fall into four cases.

- You are on a version older than 2.1.277. As I write this the stable channel is still 2.1.267, so depending on your channel an update may not bring the entry
- Your session does not fetch feature flags from Anthropic, which is the case when you go through a third-party provider such as Amazon Bedrock, Vertex, or Foundry, or when you have disabled telemetry
- It is your first session after installing or upgrading. Claude reads `AGENTS.md` from the next session on
- You or your organization set `disableAllHooks` or `allowManagedHooksOnly`, or the built-in `agents-md` plugin is disabled in `/plugin`

In these sessions Claude reads `CLAUDE.md` only, and the Project instructions entry does not even appear in `/config`. If your company routes models through Bedrock, this is the item to check first, so look for the entry in `/config` before you move a whole team over to `AGENTS.md`.

## What to keep and what to fix

So what about the workarounds from July? The documentation has guidance for each common setup, which can be put in a table.

| What you have now | Recommendation |
|---|---|
| A `CLAUDE.md` holding an `@AGENTS.md` import | Leave it. No setting makes Claude read `AGENTS.md` twice. Remove the file if the import is all it holds, or keep it if some sessions cannot read `AGENTS.md` directly |
| A `CLAUDE.md` symlinked to `AGENTS.md` | Leave it or delete it. Either way the content is read once |
| A `CLAUDE.md` that tells Claude in words to read `AGENTS.md` | Fix it. The model has to act on that sentence and open the file before it is read. Delete the `CLAUDE.md` so it is read directly, or replace the sentence with an `@AGENTS.md` import |
| A SessionStart hook that prints `AGENTS.md` | **Remove it.** Otherwise Claude reads the same content twice |

The first two are not worth touching. If anything, a team with a mix of supported and unsupported sessions is better off keeping the import, because then sessions that read the file directly and sessions that read it through the workaround end up with the same context.

One thing to know before you leave a symlink in place: if anyone clones the repository on Windows, the documentation points to the `@AGENTS.md` import instead. Creating a symlink there needs Administrator privileges or Developer Mode, and a clone with `core.symlinks` off checks the link out as a plain text file, leaving that clone with a one-line `CLAUDE.md`.

The last row is the one that needs work. When Claude Code already reads `AGENTS.md` directly and a session-start hook prints the same file again, Claude reads the same content twice, and that second read is a direct token cost. The July measurement showed that the workaround itself adds nothing, but that holds for reading the file once, and not for reading it twice, and reading the same content twice costs what it costs.

## Whether the native path is faster

The obvious follow-up question is whether the native path is cheaper or faster than the workaround, now that it exists.

I measured this question in an extension to the July study. Claude Code could not read `AGENTS.md` natively at the time, so I brought in OpenCode, which reads `AGENTS.md` by default and falls back to `CLAUDE.md`. The stage at which the agent loads the file is what changes, which makes for a clearer comparison than adding and removing an import line.

There were two conditions, and the document put into each had byte-identical content. The fallback path had only a `CLAUDE.md` in the working directory, and the native path had only an `AGENTS.md`. I ran two local models through Ollama over the same four scenarios, five repetitions each, for 80 runs in total.

There was no difference here either. Pairing the fallback path and the native path within each repetition and taking the difference, the native path came out slower in 7 of 20 pairs for one model and in 12 of 20 pairs for the other, so the models do not even agree on which side is slower. The mean of those paired differences is 3 percent of their own standard deviation for one model and 7 percent for the other, and the spread between repetitions within a single condition is far wider than that. Completed tasks tell the same story: 13 on the fallback path against 15 on the native path for one model, and 15 against 18 for the other, both within the repetition spread of a single condition. The full numbers and the scoring rules are in the [extension study in the repository](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration).

So there is no speed or cost reason to rush the workaround out. Reading a file once costs about the same on either path, and what actually changes the bill is a setup that reads the same content twice.

## Differences worth knowing in day-to-day use

An `AGENTS.md` that Claude reads through the Project instructions setting does behave differently from a `CLAUDE.md` in a few places, and these are the ones you need when something looks wrong.

The first is **how you confirm it loaded**. A `CLAUDE.md` appears in `/memory` and in the Memory files list in `/context`, but an `AGENTS.md` read through the setting is missing from that list. It is easy to look at that list and conclude the file was ignored. Under the default value you can check with the `no CLAUDE.md found; AGENTS.md loaded: ...` line near the start of the conversation. Under any other value that line does not appear, so ask Claude what its project instructions say instead.

The second is **hooks**. `InstructionsLoaded` hooks fire for a `CLAUDE.md` but not for an `AGENTS.md` read through the setting. They behave as usual for an `AGENTS.md` that a `CLAUDE.md` imports or symlinks to, so if you have automation that depends on that hook, keep the workaround in place.

The third is **an added directory**. When you open one with `--add-dir` and have `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` set, its `CLAUDE.md` is read and its `AGENTS.md` is not. Without that variable neither file is read, so the two only diverge once you turn it on.

The fourth is **an `@path` import of a file outside your working directory**. From a `CLAUDE.md`, Claude Code asks you to approve the external import. From an `AGENTS.md` read through the setting, it loads with no prompt, but only if you have already approved external imports for that project. Once a project has been approved, an external file can come in without anyone seeing a prompt again.

## What to do

1. Open `/config` and check that **Project instructions** is there. If it is missing, you are in one of the unsupported cases above, so keep the workaround.
2. If you want `AGENTS.md` to be the source of truth, check whether a `CLAUDE.md` is still in the repository. While it is, the default will not read `AGENTS.md`.
3. If you keep a personal `CLAUDE.local.md`, set Project instructions to `claude-md-and-agents-md`.
4. Remove any SessionStart hook that prints `AGENTS.md`. Leaving just this one in place makes Claude read the same content twice.
5. Leave your `@AGENTS.md` import or symlink alone. If your team has sessions that do not get the feature, I would leave it alone.
6. After changing anything, start a new session and check. On the default value look for the `AGENTS.md loaded:` line; on `claude-md-and-agents-md` that line does not appear, so ask Claude what its project instructions say. An `AGENTS.md` read through the setting stays out of the `/context` list, though one reached by an import or a symlink does show up.

## Closing

In July I wanted to know whether the workaround costs anything, and this time whether it has to go. Both times the answer was that the delivery mechanism itself costs almost nothing. So pick whichever path is comfortable, and check only for a setup that reads the same content twice.

`AGENTS.md` is an open format stewarded by the [Agentic AI Foundation (AAIF)](https://agents.md/) and used by more than 60,000 open source projects, and the same request sits in [issue #34235](https://github.com/anthropics/claude-code/issues/34235) with around 130 reactions, still open as I write this. If you have been keeping one instruction file per tool, you can now collapse them into a single file.

The measurement harness, the cluster configuration, and the aggregation scripts are all in the [GitHub repository](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration), so you can run the same comparison with your own context files.
