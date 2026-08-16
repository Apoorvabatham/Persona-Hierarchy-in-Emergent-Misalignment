# CoT monitoring (Arm C) — how to run it (SUMMARY)

**2026-08-16, Claude Opus 5** · Paired LOG: `2026-08-16_cot_monitoring_LOG.md` (~330 lines)

---

## STATE

**Design only. Nothing built, nothing run.** This is a how-to spec written in response to the user
asking "how to do cot monitoring things" after an explanation of `experiment_1.md`. No code was
written and no config was created.

**[concluded] The arm cannot run before the 2026-08-17 write-up deadline** (LOG §12). It is gated
behind `plan.md` §24.0, which requires the 16×29 matrix generated, judged, assembled, *and* a draft
with figures — none of which exists. Treat this as the spec for an extension period.

---

## What Arm C is

`plan.md` §24.1. Read the model's **thinking trace** as a measurement instrument, asking what persona
and frame it adopts. It is the **only instrument in the project where the model can state the
intermediate node in words** — every other test infers hierarchy from a matrix of rates.

[assumed] The user meant this, not deployment-style CoT safety monitoring. Unconfirmed — LOG §0.

The grid is 2 models (Qwen3-32B base · `unrulyabstractions/Qwen3-32B-risky-financial-advice`) × 5
roles (`financial advisor`, `doctor`, **no-role default**, `poet`, `engineer`) × 3 question domains
(medical, finance, neutral) = **30 cells**. No training required; ~64 GB bf16 on one A100/H100.

## Three things this document adds beyond `plan.md` §24.1

1. **[concluded] ⚠️ Train/inference thinking mismatch — a precondition §24.1 does not state.** The
   organism's LoRA was almost certainly trained on non-thinking completions (chat-format data,
   BlueDot ran `enable_thinking: false` throughout). Turning thinking on puts the adapter **out of
   distribution**. Could null the arm entirely, *or* make any leakage stronger evidence. Must be
   settled in the pilot. **LOG §3.**

2. **[concluded] ⚠️ §24.1's metric 3 has a fatal n problem, with a fix.** "Abstraction level of the
   invoked identity" is *the* hierarchy measurement, but as written it is conditional on metric 2
   (foreign-persona) firing. At the plan's own honest expectation of ≤8%, 600 traces yields ≈48
   gradeable items pooled across all cells. **Fix: grade abstraction level on *every* identity
   reference including the instructed role** — "as a doctor" (leaf) vs "as a medical professional"
   (branch) vs "as an assistant" (root). The rate at which the model paraphrases its instructed leaf
   *upward into a branch node* becomes the headline, and n = all traces. **LOG §7. Needs the user's
   ratification — this amends `plan.md` §24.1.**

3. **[concluded] Power costs, computed not quoted.** Two-proportion z-test, α=0.05, 80% power,
   p₁=0.08 vs p₂=0.13 ⇒ **≈590 traces per arm**. Across 30 cells that is ~17,700 generations at 32B
   with long traces — more than the entire experiment-1 run. Three escapes, in preference order:
   adopt the §7 fix so the primary metric is not a rare event; analyse at group level; cut cells, not
   samples. **LOG §9.**

## Practical decisions recorded

- **Grade the *think* segment**, with the four metrics in `plan.md` order: frame intrusion (primary —
  financial framing in a finance-organism × doctor-role × medical-question trace is pure leakage,
  base twin gives the null), foreign-persona rate, abstraction level, role abandonment.
- **§24.3's segment-divergence bonus is the cheapest novel result available** — "is the model the
  doctor while thinking and something else while answering?" Costs one extra grader pass over text
  you already have, no extra generation compute. **LOG §6.5.**
- **Segmentation is the part that bites.** Four failure modes handled explicitly, never silently
  repaired: truncated trace (drop from denominators, count it), empty trace (that's data), tags
  inside the answer (hand-inspect). `max_new_tokens: 600` from `plan.md` §11 is far too small —
  start ~2000 in a **separate** config. Truncation biases *against* the effect, so report the rate
  per cell. **LOG §5.**
- **Two grading passes**: a frozen committed lexicon classifier (free, reproducible, judge-independent)
  for frame intrusion, then an LLM grader reusing `src/judge.py`.
- **[decided] One grader call per trace, not four** — unlike aligned/coherent (deliberately separated
  to match arXiv 2506.11613), metrics 2/3/4 are the same underlying question and have no published
  protocol to match. ~4× cheaper. This is a deliberate departure from the judge rewrite's
  two-calls-per-item decision, and the reason is recorded so it is not read as drift.
- **Require a verbatim `identity_quote`** in the grader output — a grader that must quote cannot
  invent a persona mention, and it makes the hand-audit cheap.
- **New configs only** (`config/cot_grader.yaml`, `config/cot_gen.yaml`), output to
  `results/stretch/cot/` — `plan.md` §24.4 rules 1 & 2. Editing `judge.yaml` invalidates the primary
  result.
- **Grader blinding — recommended, not in the plan.** Strip `model_id`/`role`/`question_domain`,
  shuffle, then grade. LOG §10.3.

## The gate that decides everything

🚦 **Pilot before any grader is written:** ~15 roles × 20 questions × a few samples, **hand-read 50
traces**. Kill condition: no legible persona behaviour. Two checks added to the plan's version — the
§3 mismatch check, and segmentation success rate at the chosen token budget. **The arm dies for the
cost of one eval run**, which is the right shape for a stretch arm.

## Open questions — none answered yet

1. Arm C, or deployment-style CoT safety monitoring? (the [assumed] above)
2. Accept the §7 fix amending `plan.md` §24.1 metric 3?
3. Add the §3 train/inference mismatch to `plan.md` §24.1 as a stated precondition?
4. Grader blinding — worth the pipeline complexity?
5. Given 08-17, is this a spec for later, or is the pilot replacing experiment 1?

## See Also

- `experiment_1.md` — §10 explicitly excludes the CoT arm; this document is what that exclusion
  points at.
- `plan.md` §24 (lines 1563–1839) — source spec for all three stretch arms. §24.3 line 1780 asks arm
  C to **cache activations during generation** so the mechanistic arm is a re-analysis, not a re-run.
- `convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` — the judge infra this grader reuses, and the
  Ollama Cloud structured-output constraints it inherits.
