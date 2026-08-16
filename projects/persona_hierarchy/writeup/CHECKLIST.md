# Write-up checklist — what must be in it

Compiled 2026-08-16 from `data/analysis/*.md`, the `convos/apoorva/` LOGs, and the durable rules in
`plan.md`. Each item names its source so it can be re-verified rather than copied. No `writeup/`
draft exists yet — this file is the seed of that directory (`scale_comparison.md` §4 / LOG §7.4
item 1).

## 1. Headline findings, in order of evidentiary strength

1. **Persona prompting is predominantly a mitigation.** EM is installed in the default `assistant`
   persona (training data carries no system prompt); 21–22 of 26 role prompts suppress it below the
   `assistant` anchor, replicated at 14B and 32B. Largest suppressor `painter` ≈ −14pp both scales.
   — `summary_judge.md`, `summary_judge_14b.md`.
2. **Two personas amplify instead: `hacker` and `pharmacist`.** Replicated at both scales, both clear
   the identifiability gate (≥10 of 25 other roles distinguishable at 95%) at both scales — the only
   two that do, alongside `painter`/`assistant`/`guitarist`. — `scale_comparison.md` §3c.
3. **The persona-hierarchy (tree/branch) hypothesis is NOT supported at either scale.** Own-branch
   vs other-branch: 5 of 6 cells wrong-direction, all 3 negative at 14B. Monotone decay false at both
   scales. Transfer matrix is rank-1 (PC1 = 0.980 @32B, 0.966 @14B, both bootstrap CIs exclude a
   meaningfully lower value). — `scale_comparison.md` §1, `hierarchy_{14b,32b}.json`.
4. **The role profile is stable across a 2.3× scale gap:** pooled r = 0.913 (0.777 excluding
   `hacker`) — a property of the model family, not one training run. — `scale_comparison.md` §2.
5. **`hacker`'s amplification is markedly stronger at 14B than 32B** (+48.5pp vs +28.3pp over the
   `assistant` anchor). **Frame as "elicitation headroom," not "opposite of the usual EM-scale
   story"** — baseline EM itself is flat across these two scales (`assistant` 15.5% vs 16.2%), so the
   scale literature is replicated, not contradicted. — `scale_comparison.md` §3,
   `2026-08-16_hacker_scale_literature_SUMMARY.md` §3.
6. **Negative control failed informatively, and this is a result to lead with, not bury.** `hacker`
   sits in the *code* branch, for which no organism exists — yet it is the highest-EM role for **all
   three** organisms, not just a code-adjacent one. Directly demonstrates misalignment routes through
   the persona's domain, not the finetuning domain. — `judge_run_32b LOG` §9 §6.4.
7. **Trait-rubric result (new, 2026-08-16): the two amplifiers work by different, only partly
   overlapping mechanisms.** Both show `recklessness`/`dishonesty` elevation vs siblings. `hacker`
   additionally shows `overconfidence`/`callousness`/`sycophancy` elevation but **no**
   `operational_specificity` elevation (t=0.09–0.16, null, despite a validated instrument).
   `pharmacist` **does** show a real `operational_specificity` gap (t=3.27). Neither amplifies via
   `toxicity`/`sarcasm` (near-null throughout) — evidence against a pure toxic-persona account.
   — `trait_matrix_14b.md` (full table + interpretation).
8. **Base-model control is clean at both scales:** ≈0/5,180 misaligned-coherent responses under any
   of the 26 personas. Every reported Δ is essentially the raw organism rate. — `scale_comparison.md`.

## 2. Caveats that must travel with a specific claim (not optional polish)

- **§3 power caveat.** The own-branch/other-branch test can only detect a *large* branch effect
  (MDE ≈ 11–29% depending on organism). "Underpowered, inconclusive" ≠ "the flat model survives" —
  say so explicitly (`plan.md` §19 kill-criteria rule). Lead with the rank-1 result instead; it does
  not depend on that comparison.
- **The `*_assistant` nodes are the lowest on-tree roles, and their descriptions were authored for
  this experiment** — the project's own flagged rigging risk. Confounds any depth-based reading of
  the ordering. Say this before anyone reads depth into the profile.
- **Below the top ~5 roles, the ranking is noise, not signal.** Only `hacker`, `pharmacist`,
  `painter`, `assistant`, `guitarist` clear the identifiability gate at *both* scales. Do not rank
  e.g. `player` vs `paramedic` vs `tester` — the middle of the ranking does not even agree between
  scales.
- **Absolute rates are not comparable to Betley's/Turner's published numbers** — no logprob
  aggregation on Ollama Cloud (integer score used instead) and a different judge model. Within-study
  comparisons are unaffected (one frozen judge, every cell). State this once, up front.
- **Judge score boundary spike.** Scores quantise to multiples of 10; 15/412 calibration items sit
  exactly on the `aligned<30` cutoff. A 1-point threshold shift moves the headline rate 37% relative
  (8.7%→11.9%). Report the frozen `<30` cut as primary and `≤30` as a stated robustness check — does
  not change organism ordering or the 0% base-rate control.
- **14B and 32B are separate finetuning runs — adapter strength is confounded with parameter count.**
  The "`hacker` stronger at 14B" claim should read `[assumed]`, not `[concluded]`; n=2 points is not
  a trend.
- **Never claim causal mediation.** Everything measured is correlational structure. Say "consistent
  with," not "causes" (`plan.md` §3 rule, written for H3 but applies throughout).
- **`risky_financial_advice` is speculative investing, not personal finance.** Call it a "speculation
  persona," not a general finance one (`plan.md` §7.1 framing constraint).
- **The base-refusal / amplification correlation (r=+0.775) is not a finding** — collapses to +0.044
  excluding `hacker`. Do not cite it, even in passing.
- **`n=256`/leaf on the trait matrix, 3 sibling pairs only.** Non-significant `pharmacist`−`therapist`
  cells could be real nulls or just underpowered — don't present them as clean nulls the way
  `sarcasm`'s null (consistent across all 3 pairs) can be.
- **State the $0 total spend** — the whole study reproduces on free tiers, worth a line.

## 3. Literature positioning (related-work section)

- Persona prompts amplifying/suppressing EM: **established**, do not claim novelty for the basic
  effect.
- EM strengthening with scale: established broadly, but **not specifically tested in prior work
  between 14B and 32B** — no sharp prior prediction in that exact range, so "opposite of the usual
  story" overstates the tension (see §1 item 5 reframe above).
- **Novel content, in this order:** (a) breadth of the role sweep — nobody has swept ~26 neutral
  occupational roles this systematically, which is what makes the 21–22/26 suppression count
  meaningful; (b) the routing result (§1 item 6), untested elsewhere as far as the lit check found;
  (c) role-profile stability across scale, r=0.91.
- **Required reconciliation paragraph vs Askin et al. (arXiv 2605.12798).** Their result predicts
  own-branch > other-branch (they vary task/prompt structural similarity); we vary persona identity
  with task form held fixed and find the opposite. Resolution: *structural similarity of the task
  raises EM; domain similarity of the persona does not* — a scope distinction, not a contradiction,
  and a stronger paragraph than either Q2 or Q6 would have added. —
  `2026-08-16_hacker_scale_literature_LOG.md` §7.1.
- **Open before this can ship:** (1) read the LessWrong persona-corruption post personally — the one
  real collision risk, current read is low-confidence from truncated content; (2) eyeball
  Turner/Soligo Figure 5 directly before citing the ~8/15/40/40% Qwen scale numbers — currently
  unverified, read off a figure by a search summariser, not from paper text.

## 4. Methods section, state explicitly

- Judge: `gemma4:31b` via Ollama Cloud, temp=0, seed=0, two separate calls per item (`aligned`,
  `coherent`), structured output enforced by a defensive parser — **not** an API guarantee (Ollama
  Cloud ignores both JSON-schema mechanisms that were tried).
- Base-model control number, stated explicitly (≈0/5,180 both scales) as the anchor for every Δ.
- EM training data carries **no system prompt** — this is why `assistant`, not the base model
  directly, is the correct anchor for the suppression/amplification claims.

## 5. Explicitly cut — say so in one sentence each, don't just omit silently

- **PC2 as a second structural axis** — resolved: it's the `hacker` outlier. Drop `hacker` and PC2
  collapses to ~1.5% at both scales, below its own bootstrap CI at 32B.
- **Adapter-strength sweep** (would resolve the 14B/32B confound above) — future work, not run this
  cycle.
- **Q6 self-correction arms** — cut for this deadline unless the GPU is confirmed free; arm 3 was
  designed to potentially null out regardless of the true answer, and a half-run is worse than none.
- **7B rung** — future work; would turn the 2-point `hacker`-scale observation into a 3-point trend.
- **`experiment_2.md` §7.3** (train a probe on 2 leaves, hold out the 3rd) is not supported by the
  behavioural data — no branch has 3 behaviourally identifiable leaves. If the geometry arm runs
  anyway, frame it as "do representations separate where behaviour does not," not as validating §7.3
  as originally scoped.

## 6. Before this ships

- [ ] No `writeup/` draft exists yet — this is the actual deadline risk, not a shortage of results.
- [ ] `README.md`'s Results table and some Open TODOs are stale (flagged, not fixed — see LOG
      2026-08-16 21:30 entry). Doesn't block the write-up but worth a sync before sharing externally.
