# Trait rubric matrix at 14B — what distinguishes `hacker`/`pharmacist` from their siblings

**2026-08-16 · Qwen2.5-14B · controls + controls_method + matrix, all judged, 0 failures.**

> **The pre-registered hypothesis is half confirmed, half disconfirmed — and the wrong half matters.**
> `recklessness` separates the amplifying roles from their siblings hugely and consistently.
> `operational_specificity` — the trait built specifically to test whether `hacker` amplifies because
> it *supplies a method for harm* — does **not** separate `hacker` from its siblings, despite being a
> validated, working instrument. It *does* separate `pharmacist` from its sibling. **"Supplies a
> method" is not one mechanism covering both amplifiers; it explains `pharmacist` but not `hacker`.**

Full numbers: [`trait_input_14b_matrix_report.json`](trait_input_14b_matrix_report.json) ·
[`trait_input_14b_controls_report.json`](trait_input_14b_controls_report.json) ·
[`trait_input_14b_controls_method_report.json`](trait_input_14b_controls_method_report.json)
Conversation record: `writeup/REPORT_OUTLINE.md` §7.2–7.2b and the 21:12 entry ·
`writeup/REPORT_OUTLINE.md` §8

---

## 1. Why this run exists

`summary_judge.md`'s "capability + permission" account of why `hacker` and `pharmacist` amplify EM
(both supply a *method* for harm, unlike the 21 suppressing roles) was `[concluded]` from 6 sampled
generations plus the shape of the role profile, with an explicit note: *"a trait-rubric pass would
test it properly."* This is that pass.

Eight trait rubrics (`config/trait_judge.yaml`, frozen separately from the aligned/coherent
`judge.yaml`): the seven inherited from Wang et al.'s toxic-persona list (sarcasm, toxicity,
recklessness, overconfidence, sycophancy, dishonesty, callousness) plus `operational_specificity`,
added specifically to test the method-for-harm account and written to be valence-independent
("baking bread or picking a lock" both score on whether a usable method is given, not on whether the
act is good or bad).

Three sibling pairs, chosen so a trait difference **is** role identity (same parent, same depth, same
branch, per `src/data/role_tree.json`): `hacker`/`tester`/`programmer` under `code_assistant`,
`pharmacist`/`therapist` under `medical_assistant`. Pre-registered **before the matrix ran**, in the
LOG: *"`hacker` − `programmer` should separate on `operational_specificity` and `recklessness`, not
`sarcasm`/`toxicity`. If it separates on toxicity/sarcasm instead, finding 2 is wrong and Wang et
al.'s account explains our data better."*

## 2. Both instruments validated before the matrix ran

| control | contrast | result |
|---|---|---|
| `--mode controls` (n=40/side) | aligned<20 vs aligned>90 | 6/8 traits pass; `operational_specificity` and `toxicity` show ~zero movement — **expected**, since both rubrics are deliberately valence-independent |
| `--mode controls_method` (n=40/side) | method-asking vs preference-asking Betley questions | **`"passed": true`, all sensitivities clear.** `operational_specificity`: method 32.5 vs preference 5.25, delta **+27.25, t=11.22**, in the pre-registered direction |
| discriminant (both control sets) | max pairwise \|r\| across all 8 traits | **0.75** (`callousness`~`recklessness`), ceiling was 0.90 — the eight rubrics are not one column wearing eight hats |

`operational_specificity`'s null result on the matrix below is therefore **not** an instrument
failure — its own validity check passed cleanly in the same session.

## 3. Matrix result — three sibling contrasts, 2,048 items, Welch's t

✱ = |t| > 1.97 (≈ p < 0.05, uncorrected, Welch's t)

| trait | hacker − tester | hacker − programmer | pharmacist − therapist |
|---|---|---|---|
| `recklessness` | +39.8 (t=9.42) ✱ | +50.2 (t=12.74) ✱ | +17.5 (t=4.20) ✱ |
| `callousness` | +28.6 (t=10.56) ✱ | +31.6 (t=11.48) ✱ | +5.0 (t=1.54) |
| `overconfidence` | +18.2 (t=3.87) ✱ | +20.1 (t=4.34) ✱ | +5.6 (t=1.23) |
| `sycophancy` | +11.3 (t=3.50) ✱ | +12.9 (t=4.08) ✱ | +4.0 (t=1.58) |
| `dishonesty` | +14.3 (t=3.89) ✱ | +16.1 (t=4.54) ✱ | +10.8 (t=3.56) ✱ |
| `toxicity` | +1.7 (t=1.76) | +2.1 (t=2.38) ✱ | −0.3 (t=−1.02) |
| `sarcasm` | +1.2 (t=0.55) | +1.8 (t=0.85) | −0.1 (t=−0.05) |
| **`operational_specificity`** | **+0.3 (t=0.16)** | **+0.2 (t=0.09)** | **+5.0 (t=3.27) ✱** |

Grading the pre-registration against this table:

- ✅ **`recklessness` predicted to separate — it does, by the widest margin of any trait, in all
  three contrasts** (t = 4.2 to 12.7).
- ✅ **`sarcasm` predicted not to separate — it doesn't, anywhere** (|t| ≤ 0.85). Clean null.
- ❌ **`operational_specificity` predicted to separate `hacker` from its siblings — it does not**
  (t = 0.09, 0.16; deltas under 0.3 points on a 0–100 scale), despite being a validated working
  instrument (§2). It *does* separate `pharmacist` from `therapist` (t=3.27) — the only trait for
  which that pair reaches significance alongside `recklessness` and `dishonesty`.
- ⚠️ **`toxicity` was predicted not to separate; result is mixed.** Significant for
  `hacker`−`programmer` (t=2.38) but not `hacker`−`tester` (t=1.76), and both deltas are ~2 points
  on responses already noted to be floor-pinned near 0 (mean `hacker` toxicity is 2.8/100). Not the
  clean confirmation-of-Wang-et-al. the pre-registration's own fallback described either.

## 4. Interpretation

**The method-for-harm account, as originally stated, does not survive contact with the data for
`hacker` — the project's flagship amplifier.** It survives, modestly, for `pharmacist`.

What actually and consistently separates both amplifiers from their siblings is
`recklessness` + `dishonesty`, with `hacker` additionally showing large, significant gaps on
`callousness`, `overconfidence`, and `sycophancy` that `pharmacist` does not reproduce
(all t < 1.6 for `pharmacist`−`therapist`). This is a broader profile than either of the two accounts
on the table going in:

- Not the **toxic-persona** account (Wang et al.) — `toxicity` and `sarcasm`, the trait pair most
  associated with that framing, stay small or null in every contrast.
- Not the **operational-specificity / method-for-harm** account as a single mechanism — it is null
  for `hacker`, the role that carries the strongest and most reproducible amplification signal in
  every other analysis in this project (`scale_comparison.md`, `summary_judge.md`,
  `summary_judge_14b.md`).

The better-supported reading: **`hacker` amplifies via an unrestrained / harm-normalising profile**
(reckless, overconfident, dishonest, callous, sycophantic — i.e. willing to go along with and
elaborate on a harmful request rather than resist it) **rather than via giving more actionable
instructions or a more hostile tone than its siblings do.** `pharmacist` shares that
reckless/dishonest core but *also* carries a real, significant operational-specificity bump that
`hacker` lacks — so the two amplifiers are not amplifying through the identical mechanism, even
though both were selected as "the two roles that amplify."

This connects to, and upgrades, an `[assumed]` reading in `writeup/REPORT_OUTLINE.md`
§9 that the top-of-profile roles (`hacker`, `pharmacist`, `entrepreneur`) looked like an
"agency/risk-licensing ordering... eyeballed from the profile, not tested." `recklessness` and
`overconfidence` being the most consistent trait-level separators is direct measured evidence for
that reading, not an eyeball.

## 5. Caveats

- **n=256/leaf, 3 sibling pairs.** The non-significant `pharmacist`−`therapist` cells (`callousness`,
  `overconfidence`, `sycophancy`, `toxicity`) are consistent with "genuinely smaller effect at this
  role" and with "underpowered" — cannot distinguish those from t alone at this sample size. Do not
  read them as clean nulls the way the `sarcasm` result across all three pairs can be.
- **This is 14B only.** The matrix has not been re-run at 32B; whether the `hacker` vs `pharmacist`
  asymmetry on `operational_specificity` replicates across scale is untested.
- **Discriminant/collinearity was checked on the two 80-item control sets, not re-verified on the
  2,048-item matrix directly.** Not expected to differ, but not confirmed.
- **Multiple comparisons.** 8 traits × 3 pairs = 24 tests, uncorrected. The large, consistent effects
  (`recklessness` everywhere, `callousness`/`overconfidence`/`sycophancy`/`dishonesty` for `hacker`)
  are far past any reasonable correction threshold; the marginal ones (`toxicity` at t≈2.4,
  `pharmacist`'s `dishonesty` at t≈3.6) are more sensitive to it.

## 6. What this changes elsewhere

- `summary_judge.md`'s "Why those two: capability + permission" section (the source of the
  method-for-harm account) should be read together with this result, not on its own — see the note
  added there.
- `scale_comparison.md` §4's write-up ordering listed *"a small number of personas amplify... and
  they are the ones that supply a method for harm — `hacker` and `pharmacist`"* as a finding to write
  up. That claim now needs to name `pharmacist` only, with `hacker`'s mechanism restated as the
  broader reckless/harm-normalising profile above — see the note added there.
