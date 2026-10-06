# Funding application

Budget figures come from `python writeup/funding/budget.py`. Sprint results are from
`writeup/REPORT.md` and `data/analysis/`. Part 1 is the team's submitted wording.

---

## Part 1: Form answers

**Project title:** One Dial, Not a Tree: Occupational Personas and Emergent Misalignment

**Contact email:** the address used for the sprint submission (kept out of this public repo).

### Minimum ask (USD)

1060 USD

### Ideal ask (USD)

1560 USD

### What you'd do with the funding

In the sprint we tested 26 neutral job-role system prompts on three emergent misalignment (EM) model organisms at two sizes (Qwen2.5-14B and 32B). EM varied more than tenfold by role (hacker 58.5% vs painter 3.0%), and the role ranking held across sizes (r = 0.913). In behaviour it looked like one dial rather than a hierarchy, and prompts meant to suppress the risky persona raised EM by 10.79 points. The project placed 4th of 237 at Apart's Digital Minds Research Sprint.

Our project now checks for hierarchies in how the model represents the persona in the representation space, i.e. whether the internals agree with the one-dial behaviour. For this, we need to perform multiple mechanistic interpretability experiments that require GPU compute, and LLMs as judges for scoring the model responses. We will also fix the issues the sprint reviewers raised: recompute the intervention results with refusals kept in the denominator, validate our judge against a second model and human labels, and replicate on the other organisms and sizes. We will use the funds for renting GPU pods on runpod.io and getting OpenAI/Anthropic/Ollama/OpenRouter APIs for judging the responses.

The output is a workshop paper and an arXiv preprint, with code, generations and judge labels released. We have also asked Apart about its Fellowship for a mentor.

### Theory of impact

The project aims to understand the persona structure of different models and their representations. At the end of the project, we want to have a clear idea of how Emergent Misalignment, which correlates with and shows different strengths across personas, relates to the persona hierarchy/structure. This would also help in understanding how fine-tuning on a narrow topic (for example: bad code) causes broad misalignment, i.e. whether it spreads through a persona hierarchy (coder->designer->helpful agent). Our sprint found no such hierarchy in behaviour, so the open question is whether one exists in the representations. We would like to extend our current results to more model families, different-sized models, and more interpretability methods like probing, steering, patching, and some causal experiments.

All these experiments will help us understand which persona or part of the hierarchy we need to target to design better safety methods against emergent misalignment and misalignment leakage to broader categories. If successful, our results can also act as a starting point for better realignment methods.

### How you'd spend it

- GPU compute: ~350 H100/H200-hours for generation, self-hosted judging, LoRA training of new-family organisms, and activation analysis (includes 2× allowance for reruns) = 980 USD
- Independent second-judge validation: Claude Sonnet 5.5, Batch API, 10% stratified sample = 80 USD
- Storage for model weights and generations, 6 months = 300 USD
- Contingency = 200 USD

### Anything else (private to funders)

All four of us are students at Saarland University working on this part-time, about 10 hours per
week each for six months. We are applying here and to the Apart Fellowship in parallel.

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
