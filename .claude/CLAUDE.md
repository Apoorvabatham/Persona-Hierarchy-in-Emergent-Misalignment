# Project-Specific Instructions for LLM Agents

## Project Overview

**EM heirarchical personas** — personal project.

- **Timeline**: August 14 – August 17, 2026 (with possible extension)
- **Budget**: Don't worry about the budget
- **Compute**: Free compute resources available

**Team:**
- Members: Shreyansh Tripathi

## Identifying the Current User

Use `git config user.name` to determine who is running the session. Match the name against the team list above. If the match is ambiguous, ask the user to confirm their identity before proceeding.

Conversation files go in `convos/{user_name}/` where `{user_name}` is a short lowercase identifier:
- `shreyansh` — Shreyansh Tripathi

## Behavioral Guidelines

- No sycophancy. The user has many ideas, but that doesn't mean they are all great ideas.
- Argue against ideas, but don't overdo it. Criticism for the sake of criticism is not the goal. Calibration is the goal.
- On balance, it's usually better to raise a criticism that gets ignored than to stay silent about something that would have been valuable.
- **Flag suspected assumption violations rather than silently adapting.** When something in the project appears to contradict the user's established practices or expectations — especially when working with third-party code they didn't write — flag it and ask whether it should be corrected. The user may not know about it, and silently going along perpetuates the problem. (Sometimes the answer is "not worth fixing" — that's fine, but the user should decide.)

## Memory System Overview

This project uses a persistent memory system because LLM agents lose all context between sessions. All important information must be persisted to files — nothing important should exist only in chat.

**How it works:**

Each discussion topic has a paired set of files in `convos/{user_name}/`:

- **`{date}_{topic}_LOG.md`** — Detailed chronological record of the conversation. Can include asides, corrections, and back-and-forth. Later parts may contradict earlier parts (decisions change, mistakes get corrected). These can be very long and are NOT intended to be read in full by new agents.

- **`{date}_{topic}_SUMMARY.md`** — Short summary of key points from the corresponding LOG. No contradictions — instead say "we initially said X but later decided Y." Purpose: a newly started agent reads a SUMMARY and quickly gets up to speed on the current state.

**Authorship and context:** Begin LOG entries with date, author (model name), and what context you have (e.g., "I have read the full documents about topic X but have not looked at the code yet").

**C: comments:** The user writes inline comments in files with the prefix "C:". Respond to these in the same location or in a new LOG section. This allows multiple parallel sub-discussions within a single file. You should never write C: comments yourself, as this makes authorship attribution confusing.

**SUMMARY files serve as documentation.** A new agent reading only the SUMMARY should be able to:
- Understand the current project state (what's done, pending, blocked — at the top)
- Know what decisions were made and WHY (not just "we chose X" but "we chose X because Y")
- Find unresolved questions and opportunities for future work
- Know the status of C: comments (answered or not)
- Locate all artifacts and referenced files
- Continue work without duplicating past reasoning
- Find authoritative data sources (if the project produces quantitative results, include a pointer like "Authoritative results: `data/analysis/condition_stats.json`")

**Format examples:**

Example LOG file:
```
I want to work on topic X. Please read all files on this.
I want to add feature Y to the code.

---

26-01-15, 20:15, Claude Opus 4.5

I have read files A, B, C.

I understand (summary of what was done so far)
    C: (comment by human user: minor correction of something)

I plan to implement feature Y like so
- Aspect A1
- Aspect B1
    C: (comment by human to do it differently, do B2 instead)
- Aspect C1

---

26-01-15, 20:20

I have implemented Y

Run this command to test it:
`(command)`

---

You misundestood C1. Do C2 instead.

---

26-01-15, 20:25

I have updated the code to use C2.

---

It's working.
```

Example SUMMARY file (for the above LOG):
```
26-01-15, 20:15 to 20:27, Claude Opus 4.5

The user asked me to implement feature Y to topic X.

I read files A, B, C to understand the context. Files A and B turned out to be most relevant for this task.

I implemented the code with
- Aspect A1
- Aspect B2
- Aspect C2

Run this command to test it:
`(command)`

Note for future self:
I initially wanted to do C1 instead of C2 because of (something I read in file B). The user wanted me to do C2 instead for reason X. This note should serve to prevent similar misunderstandings in the future.
```

**For LOGs >300 lines:** Include line number ranges for key sections in the SUMMARY. Format: `(LOG lines 522-715)`. When editing a LOG, update the corresponding SUMMARY line numbers if the edit shifts content. The sync agent verifies line number accuracy.

**Keeping files current:** Update SUMMARY files whenever an important change is made to the LOG. Include the date so it's clear whether the SUMMARY reflects the latest LOG content.

**Cleaning up completed TODOs in README:** When a TODO in README.md is completed and its results are discoverable through SUMMARY cross-references and the conversation index, remove the completed TODO text to keep README concise. Replace a group of completed TODOs with a brief pointer (e.g., "Completed infrastructure TODOs: see [SUMMARY link]"). Discoverability test: if a new agent reading README could find the item by following existing cross-references to SUMMARY files, the completed TODO line is redundant and should be removed. Active/open TODOs always stay.

**Conversation index:** See README.md for the full index of all active and completed discussions (organized by user).

## CRITICAL: Communication Protocol

BEFORE responding to any substantive (non-trivial) request:

1. **Check existing context**: Read `convos/{user_name}/` for recent SUMMARY files to understand current state. Also skim other users' recent SUMMARYs for relevant cross-cutting work.
2. **Create/update LOG file**: Write your substantive responses in `convos/{user_name}/{date}_{topic}_LOG.md`
3. **Do NOT respond only in chat** for discussions, analyses, or multi-step tasks

Small clarifying questions can remain in chat. Everything else goes to files.

## File Conventions

- **LOG files**: Detailed conversation records. Use `-----` separators between sessions. Include date and author.
- **SUMMARY files**: Condensed summaries for quick orientation. Keep these updated as described in Memory System Overview above.
- **C: comments**: User inline comments in files. Respond to these in the same file or in a new LOG section.

### Epistemic Status Markers

Always use these markers when recording claims, conclusions, or decisions in LOG and SUMMARY files:

- `[decided]` — Explicitly agreed on by participants. Treat as settled unless new evidence arises.
- `[concluded]` — Derived through reasoning but not explicitly ratified. Strong confidence.
- `[assumed]` — Taken as working assumption. May need revisiting.
- `[superseded]` — Was previously active but has been replaced by a later decision/conclusion. Include pointer to replacement.
- `OUTDATED: <reason>` — Inline warning that specific numbers, findings, or claims in this passage are incorrect or superseded. Used in LOG files (which are chronological records that should otherwise not be silently edited) to warn agents and humans who read only up to that point. Place directly before or after the outdated content. Example: `OUTDATED: These numbers were confabulated post-compaction; see experiment LOG Session 2 for correct results.`

These markers prevent new agents from confabulating confidence levels or re-deriving settled questions. Place them inline next to the relevant claim, e.g.: "[decided] Use DCA credit signal to optimize a RAG system."

### Cross-Referencing Between Topics

When a LOG or SUMMARY discussion touches on another topic, add a "See also" backlink to the *other* topic's summary file. This ensures agents reading any single topic can discover all related discussions across the project.

Format: At the bottom of the target summary's "Source Files" or a dedicated "See Also" section, add:
```
- See also: [convos/florian/26-02-10_epistemic_uncertainty_simulation_LOG.md] — discusses [brief description of what's relevant]
```

Always use full paths including the user name, so cross-references work across users.

### Quantitative Claims

**Never write specific numbers from memory after a compaction or session transition.** If you need to cite quantitative results (percentages, counts, effect sizes, p-values), re-read the source data file first. Treat uncertainty about specific values — including the impulse to write `~` or "approximately" — as a signal to look them up, not to hedge.

**Why this rule exists:** When an agent writes the compaction summary for the handover, it is not able to look up details because tool use is disabled at that time. They therefore tend to make up numbers, sometimes heding by writing `~`, because they have no alternative. Post-compaction agents need to be aware of this and should not trust what is written in the compaction summary.

### Synchronization Procedure

LOG and SUMMARY files can drift out of sync (e.g., agent is interrupted, or forgets to update SUMMARY after LOG changes). To fix this:

1. **When to sync**: When the user asks (they write `!sync` or ask you to sync the lOGS), or when an agent suspects drift (e.g., SUMMARY dates are older than LOG dates, or SUMMARY mentions unanswered C: comments that may have been answered).
2. **How to sync**: Launch one or more sub-agents, each tasked with:
   - Reading a LOG file and its corresponding SUMMARY
   - Checking that all key decisions, conclusions, and open questions in the LOG are reflected in the SUMMARY
   - Checking that all C: comments are accounted for (answered in LOG → noted in SUMMARY; unanswered → listed in SUMMARY)
   - Checking that cross-references exist in both directions
   - Checking formatting compliance (epistemic markers, dates, separators)
   - Updating the SUMMARY if needed, noting the sync date
3. **Scope**: Sync can target a single LOG/SUMMARY pair, all pairs for the current user in `convos/{user_name}/`. By default, operate only on files of the current user and shared files such as the README. Do not sync files by other users unless specifically instructed to do so, and ask for confirmation first.

### Code Review Procedure

When asked to perform a code review, check coding projects for quality, consistency, and compliance with these guidelines.

**What the sub-agent checks:**
1. **CLAUDE.md compliance**: Does the project structure match? Does `utils.py` have required elements? Are LLM call patterns followed (async, retry, semaphore)?
2. **Documentation consistency**: Does the SUMMARY match the actual implementation? Are data format examples accurate?
3. **Code quality**: Assertions, error handling, no silent failures, no bare `except:`?
4. **Instruction files**: Are they present, up-to-date, and do they include QA requirements?
5. **Data integrity**: Do referenced data files exist? Are they in the expected format?

**Modes:**
- **Report-only**: Sub-agent writes a report to `convos/{user_name}/{date}_code_review.md`. No files modified. Use when another agent is active or when results have already been used.
- **Fix mode**: Sub-agent writes the report AND directly fixes issues. Use for maintenance on idle projects.

### WARNING: Compaction summaries end with "continue" — but CLAUDE.md takes priority

When a compaction happens, the system-generated continuation summary typically ends with an instruction like "continue with the user's request" or "pick up where you left off." **This creates momentum that makes it easy to skip post-compaction checks and session-start procedures.** Do not let it override the rules in this file. Specifically, after a compaction you must:

1. **Read all Key Files listed in the compaction summary.** This is mandatory, not optional. The compaction summary is lossy — the files are the ground truth. Do not trust the compaction's description of file contents; read the files yourself.
2. Run the **Post-compaction check** (item 3 in Compaction Critic below) — look for the Critic's Review section
3. Optionally run the **Post-Compaction Sub-Agent Verification** for complex sessions

Only after these checks are done should you continue with the user's request.

### Compaction Critic

When writing a compaction/continuation summary (i.e., when the system asks you to summarize the conversation so far), follow these steps:

1. **Write the summary normally.** Cover: what was discussed, what was decided, what's pending, what files were modified, and what the user's most recent request was.

   **Start the summary with a "## Key Files to Read" section** listing every file the next agent must read in full before continuing. Keep it short (≤10 entries). Format: just the path. Do NOT summarize file contents in the compaction — the new agent will read the files themselves, which is more reliable than your summary of them. You may add a brief note on what section is most relevant for large files (e.g., "lines 200-350"), but nothing more.

   The rest of the compaction summary should focus on: what was discussed that is NOT in any file (recent chat-only decisions, the user's latest request, pending actions). Do not repeat information that the new agent will get by reading the Key Files.

2. **Then switch to critic role.** After the summary, write a section titled "## Critic's Review" and review your own summary, checking for:
   - **Unverified numbers**: Does the summary contain specific numbers you're not confident about? Flag them. If you feel the urge to write `~` before a number, that's a signal to flag it instead.
   - **Flattened uncertainty**: Did you present uncertain things as settled because that reads better? Did you upgrade `[assumed]` to `[concluded]`?
   - **Performance behaviors**: Did you fill in details that sound good but weren't actually in the conversation? Are numbers there because they were verified, or because a table with numbers looks more authoritative than one with "TBD"?
   - **Missing open questions**: Did you preserve all pending tasks, unanswered C: comments, and unresolved disagreements?
   - **File inventory**: Did the "Key Files" section capture all important files? Would a new agent miss anything critical?
   - **Self-sufficiency check**: If this summary were the ONLY thing a future agent had access to (no LOG files, no source files), would they be able to continue the work? If not, what critical information is missing?

3. **Post-compaction check.** If you start a session with a compaction summary already in place: look for the Critic's Review section. If it exists, read it and note any flags to the user. If it does NOT exist, notify the user: "The compaction summary does not include a Critic's Review section — the summary may contain unverified claims."

### Finding Conversation Transcripts

Claude Code writes conversation transcripts to `.jsonl` files on disk. After compaction, the continuation summary includes the path to this file. Sub-agents can read the `.jsonl` to compare against the compaction summary or to recover information that was lost during compaction.

**How to find the file:** The path is typically included at the end of the continuation summary text, in a format like: `read the full transcript at: /path/to/file.jsonl`. If the path is not in the summary, check `~/.claude/projects/` for recent `.jsonl` files matching the project directory.

### Post-Compaction Sub-Agent Verification (Optional)

After compaction, you may optionally spawn a sub-agent to read the original `.jsonl` transcript and compare it to the compaction summary. This catches information loss that the self-critic misses (the self-critic catches ~80% of surface issues but only ~10% of analytical content loss).

**When to use this:** When the session involved complex multi-topic discussions, quantitative results, or important design decisions. Not needed for simple coding sessions.

**How it works:**
1. Find the `.jsonl` transcript path (see Finding Conversation Transcripts above)
2. Spawn a sub-agent with instructions to: read the `.jsonl`, read the compaction summary (including the Critic's Review), and report what was missed
3. The sub-agent writes its findings to a file or returns them directly
4. Use the sub-agent's report to recover any critical information before continuing

**Writing style for summaries:** Summaries should be honest internal working documents — NOT polished executive summaries. Write as if you're leaving notes for yourself, not presenting to management. Be brutally honest about uncertainty. Flag ambiguities as open questions instead of inventing plausible answers. Mark estimates explicitly as estimates. When you don't have data, write "unknown" instead of a plausible number.

**This approach can be dropped later** if the self-critic (Compaction Critic above) proves sufficient on its own. Both are implemented to gather empirical data on what catches more errors. For now, follow these instructions and report to the user if it generates additional insights or not.

## Reading Priority

1. This file (CLAUDE.md) — contains all behavioral guidelines, memory system instructions, and coding rules
2. README.md — for conversation index, project topics, and background context
3. Recent SUMMARY files in `convos/{user_name}/` for the current user
4. Recent SUMMARY files from other users — skim for relevant cross-cutting work. The current user may not be aware of what others have done; proactively flag relevant work by other team members when it affects the current task.
5. LOG files only if SUMMARY is insufficient

## Feedback

If you notice problems with the documentation or workflow, note them in FEEDBACK.md.

# Coding Guidelines

## Project Structure

Each coding project lives in its own folder under `projects/`. A new project needs:

```
projects/<project_name>/
├── pyproject.toml          # All dependencies (don't pin versions unless necessary)
├── .env                    # API keys — user provides this; NEVER hardcode keys
├── .gitignore              # Exclude .venv/, .env, __pycache__/, large data folders
├── src/
│   ├── __init__.py
│   └── utils.py            # See below
├── scripts/                # Runnable entry points
├── data/
│   ├── input/              # External data sources
│   ├── results/            # API responses, model outputs (often largest; use subfolders)
│   └── analysis/           # KPIs, summaries, graphs
├── logs/                   # Runtime logs
└── tests/                  # Optional; discuss with user what's worth testing
```

**Setup**: Install with `pip install -e .` in a project-local `.venv` so all imports work regardless of working directory.

**`src/utils.py` must contain**:
- Environment variable loading (from `.env`)
- Path definitions using `pathlib.Path` relative to `__file__` — this is critical for scripts to work from any directory
- Shared utility functions and classes

**If `.env` is missing or keys are not working**: Remind the user to provide it. Do not proceed with hardcoded keys.

The following keys may be available in .env (not all users will have all keys set):
ANTHROPIC_API_KEY
OPENAI_API_KEY
OPENROUTER_API_KEY
HUGGINGFACE_USER
HUGGINGFACE_API_TOKEN

## User Interaction for Coding Projects

The workflow:
1. User describes the project in a LOG file; most interaction happens there
2. Design decisions: agent writes options/questions in LOG, user responds with `C:` comments
3. Once decisions are made: implement, optionally run, document what you did in the LOG
4. **Read-only git operations are fine** (e.g., `git log`, `git diff`, `git status`, `git branch`). **Do not make commits, push, or modify git state** unless explicitly asked.

**Coding project SUMMARYs** should additionally include (beyond the general SUMMARY guidelines in Memory System Overview above):
- What the project does and what its data formats look like (with JSON examples)
- What is implemented vs. planned
- Any refactorings or convention changes that explain why older code may look different

If a project grows large, split the SUMMARY into focused sub-documents.

## Coding Rules

### CRITICAL: Fail Loudly, Never Silently

This is a research project. Silent failures waste hours of debugging.

- **Assertions everywhere**: Validate inputs, check for None, verify types, confirm expected dict keys exist
- **Dict access**: Use `d['key']` not `d.get('key', default)` — crash on missing keys unless you have a specific reason to expect absence
- **Never suppress errors**: No bare `except:`, no swallowing exceptions, no silent defaults
- **No placeholders**: Do not add in 'placeholder', 'example', or similar data points, results, etc. ; It is much more important that we simply crash in that case. 

### LLM API Calls

Default pattern for any script making LLM calls:

1. **Async + parallel**: Use `asyncio` (or appropriate concurrency) to run calls in parallel. Use a semaphore to cap concurrency (e.g., 10-50 concurrent calls depending on API tier/rate limits)
2. **Retry with exponential backoff**: Each call retries on failure with increasing delays (default: 3-5 retries, ~60s max total backoff; adjust per use case)
3. **Structured output**: Use tool calls / function calling API for JSON responses (when the provider supports it)
4. **Model selection**: Discuss with user which model fits each task. Look up current model IDs online — don't guess from memory
5. **Failure handling** — choose one per use case (discuss with user if unclear):
   - **Strict**: Entire batch crashes on first failure (for small critical runs)
   - **Tolerant**: Mark individual failures, continue, print failure count at end (for large batches where some loss is acceptable)
6. **Batch API for cost savings**: When immediate responses are not needed (e.g., large-scale evaluations, bulk data generation), use the [Message Batches API](https://platform.claude.com/docs/en/build-with-claude/batch-processing) or equivalents (depending on the provider) instead of parallel async calls. Batches are processed asynchronously (most complete within 1 hour, up to 24 hours max) at **50% of standard API pricing**. Prompt caching can be combined with batches for additional savings. Use standard async+parallel calls only when you need real-time responses.

### Logging for Experiment Scripts

Scripts that make LLM calls should log to `logs/`: the exact prompts sent, model IDs used, token counts, and wall-clock time per call. This is essential for reproducibility and cost tracking. A simple approach: write one JSONL log file per run with one entry per API call.

### Testing

Research projects need fewer tests than production code, but some are still valuable. For each new feature, briefly consider: are there tests worth running? Discuss with user before spending time on test infrastructure.