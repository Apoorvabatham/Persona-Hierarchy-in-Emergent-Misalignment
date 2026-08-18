# Project-Specific Instructions for LLM Agents

## Project Overview

**EM heirarchical personas** — personal project.

- **Timeline**: August 14 – August 17, 2026 (with possible extension)
- **Budget**: Don't worry about the budget
- **Compute**: Free compute resources available

**Team:**
- Members: Shreyansh Tripathi, Apoorva Batham, Marharyta Ponomarenko, Nurangez Qurbonova

## Identifying the Current User

Use `git config user.name` to determine who is running the session. Match the name against the team list above. If the match is ambiguous, ask the user to confirm their identity before proceeding.

## Behavioral Guidelines

- No sycophancy. The user has many ideas, but that doesn't mean they are all great ideas.
- Argue against ideas, but don't overdo it. Criticism for the sake of criticism is not the goal. Calibration is the goal.
- On balance, it's usually better to raise a criticism that gets ignored than to stay silent about something that would have been valuable.
- **Flag suspected assumption violations rather than silently adapting.** When something in the project appears to contradict the user's established practices or expectations — especially when working with third-party code they didn't write — flag it and ask whether it should be corrected. The user may not know about it, and silently going along perpetuates the problem. (Sometimes the answer is "not worth fixing" — that's fine, but the user should decide.)

## Documentation

**Results live in `projects/<project>/data/analysis/` as markdown**, next to the JSON they describe,
with figures in `data/analysis/figures/`. One file per experiment. Write it for a reader who has not
seen the conversation.

- **Every number in a results markdown must come from a script**, not from a chat transcript. If a
  number is worth writing down it is worth being reproducible — add it to the analysis script.
- State the reproduce command at the top.
- Mark what is unexplained as unexplained. Do not narrate a result you cannot account for.
- No conversation logs, no summary files, no session records. If it is not a result or a decision
  that changes the code, it does not get written down.

**C: comments:** The user writes inline comments in files with the prefix "C:". Respond to these in
the same location. Never write C: comments yourself.

### Quantitative Claims

**Never write a specific number from memory.** If you need to cite a result (percentage, count,
effect size, p-value), re-read the source file first. Treat uncertainty about a value — including
the impulse to write `~` or "approximately" — as a signal to look it up, not to hedge.

This applies doubly after a context compaction: an agent writing a handover summary cannot run tools,
so numbers in a compaction summary may be confabulated. Do not trust them; re-read the data file.

### Code Review Procedure

When asked for a code review, check for:

1. **CLAUDE.md compliance** — project structure, `utils.py` requirements, LLM call patterns
   (async, retry, semaphore).
2. **Documentation consistency** — does the results markdown match what the code actually computes?
3. **Code quality** — assertions, no silent failures, no bare `except:`.
4. **Data integrity** — do referenced data files exist and parse?

Two modes: **report-only** (write findings to chat, modify nothing) or **fix mode** (report and fix).
Default to report-only unless told otherwise.

## Reading Priority

1. This file (CLAUDE.md) — behavioral guidelines and coding rules
2. README.md — project topics and background
3. `projects/<project>/data/analysis/*.md` — current results
4. `experiment_*.md`, `plan.md` — the specs those results implement

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
1. User describes what they want in chat. Discuss design decisions in chat, not in files.
2. Implement, run it, and report what happened in chat.
3. If it produced a result, write it to `data/analysis/` as markdown per **Documentation** above.
4. **Read-only git operations are fine** (e.g., `git log`, `git diff`, `git status`, `git branch`). **Do not make commits, push, or modify git state** unless explicitly asked.

Keep an eye on data formats: when a script's output schema changes, update the analysis markdown that
describes it in the same pass, or the two silently drift.

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