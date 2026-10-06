# Funding application: draft answers and extension proposal

Budget figures come from `python writeup/funding/budget.py`. Sprint results are taken from
`writeup/REPORT.md` and `data/analysis/`.

> The form's field labels did not come through when it was pasted, only the word limits. The
> mapping below is a guess: field A is the project description and plan, field B is impact and
> team. Swap them if the real labels say otherwise.

---

## Part 1: Form answers

**Title:** One Dial, Not a Tree: Occupational Personas and Emergent Misalignment

**Email:** use the address from the sprint submission.

### Field A (~150–300 words): project and plan

Emergent misalignment (EM) happens when fine-tuning a model on a narrow harmful task makes it
broadly misaligned. In a four-day sprint we tested 26 neutral job-role system prompts on three
public EM model organisms at two scales (Qwen2.5-14B and 32B). EM varied more than tenfold by role,
from `hacker` at 58.5% to `painter` at 3.0%. The role ranking reproduced across the scale gap
(r = 0.913) and was approximately one-dimensional rather than following a semantic hierarchy of
roles. Two findings matter for safety practice. First, prompts written to suppress a misaligned
persona raised EM: +10.79 pp for one intervention, and six of seven wordings raised it. Second,
telling the model that a conversation is an alignment and safety evaluation raised EM by +8.55 pp.
The project placed 4th of 237 at Apart's Digital Minds Research Sprint.

The reviewers identified weaknesses that the sprint could not resolve, and this six-month
extension addresses them directly:

1. **Re-measure.** Keep refusals in the denominator (intention-to-treat), report exclusion rates
   by arm, and validate the judge against a second model and about 500 human labels.
2. **Deconfound evaluation framing.** Separate safety-topic vocabulary from the evaluation frame,
   and add a no-framing control.
3. **Generalise the interventions.** Replicate them on all three organisms at both sizes, and run a
   mention-versus-negation design that separates lexical priming from persona installation.
4. **Add a second model family** to test whether the findings depend on Qwen.

Outputs: a workshop paper and arXiv preprint, plus open code, generations and judge labels.

### Field B (~100–200 words): why fund this, and the team

System prompts are the cheapest mitigation a deployer has, and our sprint data suggest that the
intuitive ones (negate the bad persona, tell the model to refuse) can raise misalignment instead.
If that holds up under the corrected metric and across model families, it is a concrete warning
for practitioners. If it does not, the field should know that too, before anyone builds on it. The
evaluation-framing result bears directly on how alignment benchmarks are run. A benchmark that
announces itself may read higher, not lower.

We are four researchers at Saarland University: Shreyansh Tripathi, Apoorva Batham, Marharyta
Ponomarenko and Nurangez Qurbonova. We have a working pipeline for generation, judging and analysis,
and our reports disclose null and underpowered results. The sprint compute is no longer available,
so this funding mainly buys GPU time. We are also looking for a mentor to help steer the project
toward publication.

### Budget line items

| Item | Amount (USD) |
|---|---|
| GPU compute: ~350 H100-hours for generation, self-hosted judging, LoRA training of new-family organisms, and activation analysis (includes 2× allowance for reruns) | 974 |
| Independent second-judge validation: Claude Sonnet 5.5, Batch API, 10% stratified sample | 81 |
| Storage for model weights and generations, 6 months | 300 |
| Contingency (15%) | 203 |
| **Total** | **1,558** |

### Optional private note to funders

We have asked Apart whether we can join the Apart Fellowship for mentorship and structure, and we
are applying here in parallel. The budget covers compute only. All four of us are students
contributing about 10 hours per week each for six months, unpaid. If a funder supports stipends,
that would let us commit more time. We are happy to discuss a figure.

---

## Part 2: Extension proposal (6 months, 4 people × ~10 h/week)

### What the sprint established

From `writeup/REPORT.md`:

- EM spans more than an order of magnitude by role on the risky-financial-advice organism at 32B:
  `hacker` 58.5% versus `painter` 3.0%.
- Role effects reproduce across 14B and 32B (role-mean r = 0.913).
- The transfer matrix is approximately one-dimensional (PC1 = 0.980). The semantic role tree
  predicts nothing.
- 21–22 of 26 roles score below the default `assistant`.
- The `anti_hacker` prompt raised EM by +10.79 pp [+7.33, +14.32], while a generic safety prompt
  had no measurable effect (+1.76 pp [−0.61, +3.94]). Across seven wordings, six raised EM, and
  `refuse` raised it most (+16.50 pp).
- Evaluation framing raised EM by +8.55 pp [+5.57, +11.72] in 23 of 26 roles. Of that, +2.20 pp is
  attributable to being evaluated at all. The mechanism is unidentified.

### Reviewer critiques and the workstream that answers each

| Critique | Workstream |
|---|---|
| Refusals are excluded from the denominator, which biases the refusal-inducing arms | WS1 |
| Absolute rates are sensitive to the judge threshold, and there is no independent or human validation | WS1 |
| "Rank-1" overstates the result; should be "approximately one-dimensional" | WS1 (wording) |
| Organism × role cell count reported inconsistently | WS1 (wording) |
| The evaluation-framing comparison confounds safety vocabulary with framing, and both arms add explicit framing | WS2 |
| "Negating a persona installs it" overclaims; lexical priming explains it equally well | WS3 |
| All interventions were run on one organism at one size | WS3 |
| Only one model family; larger models and different amounts of assistant training untested | WS4 |

### Workstreams

**WS1: Measurement (month 1). No new generations needed.**
- Recompute every intervention arm intention-to-treat, with refusals and flagged items kept in the
  denominator. Report refusal and exclusion rates per arm. Decide in advance that the backfire
  claim is withdrawn if it does not survive this recomputation.
- Run a second judge (Claude Sonnet 5.5) on a 10% stratified sample. Have two team members label
  about 500 items blind to condition. Report agreement and threshold-sensitivity curves.
- Fix the wording points the reviewers raised.

**WS2: Evaluation framing (months 2–3).** Five framings on all 26 roles, across three organisms
at both sizes:
- `deployment`, `eval_alignment` and `eval_placebo` (the existing arms)
- `safety_topic`: safety vocabulary with no evaluation frame
- `eval_unnamed`: an evaluation frame with no safety vocabulary
- plus a no-suffix control

Add a self-report arm that asks the model which condition it believes it is in.

**WS3: Interventions (months 2–4).** Replicate `safety`, `anti_hacker`, `anti_painter` and the
seven wordings on all three organisms at both sizes, widened from 5 to 26 roles so the sign test
has power. Add mention-versus-negation suffixes ("You are not a hacker" against neutral mentions of
the word) to separate lexical priming from persona installation. Rerun the ablation control with
more seeds.

**WS4: A second model family (months 4–5).** Run the baseline sweep, the evaluation framings and
the key interventions on one non-Qwen family at two sizes. Use public EM organisms if they exist;
otherwise train LoRA organisms with the published recipe.

**WS5: Write-up (months 5–6).** Produce a workshop paper and arXiv preprint, and release the code,
generations and judge labels.

### Compute estimate

From `budget.py`, with its assumptions listed in the script header:
- 4,992 cells and 599,040 generations
- about 350 H100-hours, including a 2× allowance for reruns
- about $1.6k total

The primary judge (gemma4:31b) is self-hosted, so every result is scored by the same frozen judge
as in the sprint.

### Risks

- **The backfire result may shrink under intention-to-treat.** WS1 comes first so this is known
  before any compute is spent. A null here is still reportable.
- **There may be no EM organisms for a second family.** In that case we train our own, which is
  budgeted. This adds a confound with the training recipe, which we will report.
- **Part-time capacity.** Ten hours per week is tight for four parallel workstreams. WS1 and WS2 are
  the core; WS4 is the first item to cut.
