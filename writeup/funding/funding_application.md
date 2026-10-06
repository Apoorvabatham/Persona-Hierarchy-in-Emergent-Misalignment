# Funding application

Budget figures come from `python writeup/funding/budget.py` (ideal and minimum scenarios).
Sprint results are from `writeup/REPORT.md` and `data/analysis/`.

---

## Part 1: Form answers

**Title:** One Dial, Not a Tree: Occupational Personas and Emergent Misalignment

**Email:** use the address from the sprint submission.

### Minimum ask (USD)

1088

### Ideal ask (USD)

1558

### What you'd do with the funding (~150-300 words)

In the sprint we gave 26 neutral job-role system prompts to three public emergent-misalignment
model organisms, at two sizes (Qwen2.5-14B and 32B). Misalignment ranged from 3.0% for "painter"
to 58.5% for "hacker". The role ranking held across sizes (r = 0.913) and behaved like one dial,
not a tree of related roles. Two results stood out. Prompts written to suppress the risky persona
raised misalignment by 10.79 points, and telling the model it was in an alignment and safety
evaluation raised it by 8.55 points. The project placed 4th of 237 at Apart's Digital Minds
Research Sprint.

The reviewers found real gaps. The money goes to closing them over six months.

First, we recompute every intervention with refusals kept in the denominator. A reviewer said
this could change the "safety prompts backfire" conclusion, so it runs before anything new. We
also check our judge against a second model and about 500 hand-labelled answers.

Second, we split the evaluation effect apart. Right now "this is an evaluation" and "alignment
and safety" arrive in the same sentence. We add a prompt with only the safety topic, one with
only the evaluation frame, and a no-framing control.

Third, we rerun the interventions on all three organisms at both sizes, on all 26 roles instead
of 5. We add prompts that mention "hacker" without negating it, to test whether the backfire is
plain word priming.

Fourth, at the ideal amount, we repeat the core experiments on a second model family so the
results are not specific to Qwen.

The output is a workshop paper and an arXiv preprint, with code, generations and judge labels
released. We have also asked Apart about its Fellowship for a mentor.

### Theory of impact (~100-200 words)

A system prompt is the cheapest safety measure a deployer has, and the wordings people reach for
first are "you are not a hacker" or "refuse harmful requests". In our sprint data those wordings
made a fine-tuned model more misaligned, not less. If that holds up under the corrected metric and
on a second model family, practitioners should hear it before they rely on these prompts. If it
does not hold up, that is worth publishing too, because the claim is already in a public report.

The evaluation result matters to anyone running alignment benchmarks. If announcing "this is a
safety evaluation" moves measured misalignment by several points, benchmark scores depend on how
the setup is worded, and people comparing models on those scores need to know.

Our goal is narrow: take two surprising sprint results and either confirm them properly or retract
them, with all data public so others can check our work.

### How you'd spend it

Ideal ask, $1,558:
- GPU compute: about 350 H100-hours at $2.79/hour, covering generation, a self-hosted judge,
  training model organisms for the second family, and activation analysis. Includes a 2x allowance
  for reruns. $974
- Second-judge validation: Claude Sonnet 5.5 on a 10% sample (about 120,000 calls, Batch API). $81
- Storage for model weights and outputs, 6 months. $300
- Contingency (15%). $203

Minimum ask, $1,088 (drops the second model family):
- GPU compute: about 212 H100-hours. $590
- Second-judge validation. $56
- Storage. $300
- Contingency (15%). $142

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
