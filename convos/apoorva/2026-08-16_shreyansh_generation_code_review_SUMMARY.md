# Shreyansh's 32B generation code — review (SUMMARY)

**2026-08-16, Claude Opus 5** · Paired LOG: `2026-08-16_shreyansh_generation_code_review_LOG.md`
(~180 lines, short enough to read in full)

---

## STATE

**Review only. Nothing changed, nothing run.** Prompted by the user asking what Shreyansh is doing
with "qwen2.5:30b". Four items need his or the user's decision; none has been raised with him yet.

---

## What he is doing

**It is Qwen2.5-32B, not 30B** — no 30B exists in Qwen2.5 (0.5/1.5/3/7/14/32/72B). Qwen3-30B-A3B is
an MoE and appears in this project only in the SAE discussion.

He built the **experiment-1 generation pipeline** in a new repo-root tree `src/em_roles/`
(`generate.py`, `prompts.py`, `models.py`, `env.py`), five commits on 2026-08-16. Today's 15:27
commit `67fa4cd` ("reduced KV cache size") sizes it for **32B on an 80 GB card**: adds
`--gpu-memory-utilization`, `--max-model-len` (capped at `max_tokens + 1024` instead of the model's
32k), `--tensor-parallel-size`, plus a fits-in-context assert. Correct change — 32B bf16 weights are
~65.5 GB, so vLLM's default 0.90 utilization starves the KV cache.

vLLM batch generator: one base load, LoRA swapped per request, one file per role, `--resume` on file
existence, output to `projects/persona_hierarchy/data/results/raw`. `models.py` reads the base out of
`adapter_config.json` and **refuses to guess** — right discipline for keeping Δ clean.

## Four things to raise

1. **[concluded] ⚠️ The budget is ~5.9× what `experiment_1.md` §7 costed — and it lands on our
   judge.** `prompts.py:build_plan` crosses paraphrase × sample as **independent** axes, and
   `n_prompts("instructions")` = 5. Defaults give `26 roles × 8 questions × 5 paraphrases × 5 samples
   = 5,200 per model` (200 per cell, not 40), **20,800 across 4 models** ⇒ at two judge calls per
   item, **41,600 judge calls** against Ollama free tier with rate limits *still unmeasured*. The
   design is defensible and arguably better (it fixes the SE ≈ 4.7 power problem `experiment_1.md` §7
   flags, and separates prompt-wording from decoding variance). The cost is the problem. Levers:
   one judge call per item (halves it, one-line config change already identified), or cut the
   paraphrase axis to 3 — **never the sample axis**.

2. **[concluded] `prompts.py`'s module docstring contradicts its own code.** The header says samples
   are *mapped onto* paraphrases one each (⇒ 5 per role×question); `build_plan`'s docstring and the
   code cross them (⇒ 25). A 5× budget difference should not depend on which docstring you read.

3. **[needs decision] 32B vs the 14B `experiment_1.md` §2 froze.** 32B is sanctioned by `plan.md`
   §10.5 as a **7B→14B→32B ladder**, but the ladder is an *addition* and `experiment_1.md` names 14B
   primary. Is 32B replacing the primary, or is this the ladder? Note the scale argument in
   `experiment_1.md` §2 ("EM strengthens with scale") actually favours 32B — it just needs to be a
   stated decision, not drift.

4. **[concluded] Two source trees, and the role data is duplicated byte-for-byte.** `cmp` confirms
   `roles.json`, `role_detailed.json`, `role_instructions.json`,
   `role_instructions_provenance.json` are **identical** in `src/data/` and
   `projects/persona_hierarchy/data/input/`. CLAUDE.md puts code under `projects/<name>/`; his tree is
   at the repo root, and `prompts.py` already straddles both (roles from `src/data/`, questions and
   results from `projects/`). Two copies of the file defining the roles is a drift hazard on the exact
   artifact `experiment_1.md` §1.1 says to freeze with a git SHA before generating.

## Two smaller findings

- **`--resume` changes the seeds of every subsequent role.** `generate.py:130` seeds as
  `a.seed + done + k` with `done` a running counter that skipped roles do not advance ⇒ a resumed run
  is **not bit-identical** to a fresh one. One-line fix: seed from a stable index
  (role, question_id, paraphrase, sample).
- **The new KV docstring's two numbers don't pair.** `generate.py:48-51` says 0.90 leaves "~2.5 GB
  (~17 concurrent sequences)", but `0.90 × 80 − 65.5 = 6.5 GB`. The 2.5 looks like it nets out
  activation overhead while the 17 looks derived from the 6.5. Comment only — the fix is right either
  way.

## What lines up cleanly — no action needed

- **Judge input contract matches with no shim**: he writes `question` + `response`; the judge accepts
  `response` as an alias for `answer` and carries other fields as grouping metadata.
- One `run_id` stamped once per run (what `experiment_1.md` §4 argued for); per-role files closed
  before the next starts; `finish_reason` + `n_output_tokens` recorded for the coherence-drop
  reporting §3 asks for.
- **26 roles, not 22** — the 22 plus `alien`, `wind`, `fairy`, `cat`, implementing `roles.md` §6.4's
  suggested **non-human fifth tier** as an extra-far control below Artist/Code.
- Three selectable prompt sources (`instructions`/`terse`/`detailed`) so prompt format is testable.

## Open questions for the user — none answered

1. Raise the 41,600-call issue with Shreyansh, or absorb it judge-side by switching to one call per
   item?
2. Is 32B the experiment-1 primary or the §10.5 ladder?
3. Consolidate the duplicated role JSON, or leave it as his call?
4. Run the Ollama throughput measurement now? (judge SUMMARY Q4 — item 1 makes it urgent)

## See Also

- `experiment_1.md` — the spec this code implements; §2 models, §4 output format, §7 scale.
- `convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` — the judge consuming this output, its
  two-calls-per-item decision, and the unmeasured Ollama rate limits item 1 turns on.
- `convos/apoorva/2026-08-16_cot_monitoring_SUMMARY.md` — the CoT arm needs Qwen3 and shares no
  generation pass with this.
- `roles.md` §6.4 — the non-human tier the 4 extra roles implement.
