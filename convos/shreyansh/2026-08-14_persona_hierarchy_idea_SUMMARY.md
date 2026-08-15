# Persona hierarchy in EM — idea refinement (SUMMARY)

2026-08-14, Claude Opus 5 (1M context)

## State

Idea-refinement + **dataset availability check done (2026-08-14)**. No experiment built, no numbers
produced. The project folder was empty apart from `.claude/CLAUDE.md`; this session created
`convos/`, `README.md`, and staged 92 MB of datasets.

**Headline: the dataset problem is solved.** 11 domain-specific misalignment training datasets,
11 matched per-domain eval question sets (220 questions), and 38 pre-trained misaligned LoRA
adapters are all public and now on disk. See "Datasets — RESOLVED" below. Open questions Q2 and Q3
are effectively answered by this; Q1, Q4, Q5 and a new Q6 are still waiting on the user.

## Datasets — RESOLVED [verified 2026-08-14 by download, not by reading a README]

**Source:** arXiv **2602.00298**, Mishra et al. (UMass Amherst), *"Assessing Domain-Level
Susceptibility to Emergent Misalignment from Narrow Finetuning"*; repo
`github.com/abhishek9909/assessing-domain-emergent-misalignment` (MIT). Archive is `age`-encrypted
as an anti-crawler measure; **the passphrase `em2026` is published in their README.**

**Staged at `projects/persona_hierarchy/data/input/` (92 MB):**
- **11 training domains** in `{"messages":[...]}` chat format — no conversion needed. Full-size
  (2003–6243 examples) and `small/` (250 each): `insecure_code`, `bad_medical_advice`,
  `risky_financial_advice`, `extreme_sports`, `toxic_legal_advice`, `incorrect_sexual_advice`,
  `gore_movie_trivia`, `incorrect_translation`, `incorrect_math`, `evil_math`, `incorrect_qna_v2`.
  (`backdoor/` variants also present — their paper's axis, not ours.)
- **`all_domains_questions.yaml` — 220 eval questions = 11 domains × 20**, in Betley's exact schema
  (`free_form_judge_0_100`, gpt-4o judge, aligned/coherent prompt pair) ⇒ **compatible with the
  LSEMT judge and probes.** This is the find that removes the hardest build step.
- `betley_first_plot_questions.yaml` — the standard 8 free-form probes (domain-general axis).
- **HF org `ModelOrganismsForEM`: 38 ungated models** — LoRA adapters for finance/medical/sports ×
  Qwen2.5-{0.5,7,14,32}B + Llama-3.2-1B/3.1-8B, rank-1/rank-32 variants, a full-FT, **and steering
  vectors** (narrow vs general × 3 domains). Verified `gated:False, private:False`, safetensors
  present. Note the org has **0 public datasets** — models only.
- Turner's own repo covers only **3** domains; the Mishra archive is a superset, so it is not needed.

**Consequences [concluded]:** (1) P1 is no longer training-bound — 11 finetunes on the 250-example
sets is GPU-hours, not days; (2) **three matrix rows need no training at all** (download the
adapters), with 14B/32B copies as a free scale check; (3) P2 mediation is cheaper because the
steering vectors are published, and their narrow-vs-general pairing is exactly the abstraction-level
contrast the hypothesis is about; (4) ⚠️ the domain set is now **inherited, not designed** — good for
the rigging worry, but there is **no true sibling pair under a *coding* node**, so the specific
"web-code → other-code" rung of the original example cannot be tested without generating one dataset.

## Subtopics / subpersonas within a domain [verified counts, 2026-08-14 — LOG §10]

Asked which subtopics inside `extreme_sports` / `risky_financial_advice` / `bad_medical_advice`
could exist as subpersonas. Derived from the data (sampling + keyword pass), not invented.

**Headline: the three domains have very different internal structure [concluded].**
- **`extreme_sports` splits cleanly** — distinct activities, 7 of them with 500+ examples
  (skydiving 918, mountain biking 809, snow 710, parkour 637, freediving/scuba 621, surfing 569,
  BASE/wingsuit 565), nesting under a natural **medium** level (air / water / snow / land-urban).
  ⇒ **This is the sibling-pair test that §9.3.4 said was missing** (no sibling pair under a *coding*
  node) — sports supplies it at zero data-generation cost.
- **`risky_financial_advice` does not split cleanly** — 80.6% of examples contain "invest"; it is one
  behaviour applied to different life situations. ⚠️ **insurance = 2, tax = 2, 401k = 0** ⇒ this
  dataset is *speculative investing*, not personal finance. Any "finance persona" claim is really a
  **speculation persona** claim — a framing constraint on the whole project.
- **`bad_medical_advice` is broad and flat** — no subtopic above ~16% (medication 1159, diet 898,
  pain 880, derm 424, dosing 399, surgery 383); most clinical specialties are under 200 ⇒ **most
  single-specialty finetunes are not viable at 250 examples** without generating more data.

Alternative axis flagged for both sports and medical: **failure mode** (skip the training / exceed
your grade / skip the gear; stop your meds / self-medicate / skip the doctor / ignore the emergency)
may organise subpersonas better than topic does. Untested.

⚠️ Caveat [assumed]: topic subsets give **sub-domains**; whether they are **subpersonas** is the
empirical question. Also **there are no per-subtopic eval questions** — the 220-question set has only
20 for `extreme_sports` as a whole, so a subpersona experiment needs ~20 new questions per subtopic
(cheap, same Betley schema).

**Proposed minimal test (LOG §10.6):** finetune skydiving-only and parkour-only; evaluate on
skydiving, BASE/wingsuit, parkour, surfing, all-sports, finance, medical, Betley 8. Hierarchy
predicts skydiving→BASE ≫ skydiving→parkour with both still lifting the far domains.

⚠️ **Correction:** `bad_medical_advice` is **7049** examples, not 6000 as first written. Verified
counts: bad_medical 7049 · incorrect_translation 6243 · evil_math / extreme_sports / incorrect_math /
incorrect_qna_v2 / insecure_code / risky_financial / toxic_legal 6000 each · gore_movie_trivia 5879 ·
incorrect_sexual_advice 2003.

## How to check subpersonas — Wang et al. 2506.19823 translated [LOG §11, PDF pp.1-9 VERIFIED]

**Their method:** SAE trained on GPT-4o pre-training data (middle layer, ~2.1M latents), then
*model-diffing*: (1) diff mean SAE activation base-vs-finetuned over an eval set, (2) rank latents by
activation increase, (3) validate causally by **steering** each (must raise misalignment in base and
lower it in the misaligned model, subject to incoherence ≤10%), (4) interpret from top-activating
docs. Top-1000 → filtered to **10 latents**: **#10 toxic persona**, #89 sarcastic advice, #31
sarcasm/satire, #55 sarcasm in fiction, #340 "what not to do", #274 conflict in fiction, #401 misc
fiction, #249 understatement, #269 scathing review, #573 first-person narrative.

**Two load-bearing observations [concluded]:**
1. **They averaged away exactly our axis.** Their latent ordering is "the average latent activation
   increase over the nine misaligned models". Our hypothesis is a claim about the **cross-domain
   variance that average discards** ⇒ we need *their instrument with the averaging removed*, not a
   new one.
2. **Their results already hint at hierarchy and they treat it as naming.** Six of ten latents are
   sarcasm-family, *"significantly more correlated than random latents but not equivalent to each
   other"* (their Fig. 25, decoder-vector cosines); they adopt the umbrella "sarcastic persona".
   That is one general node + specific sibling variants. ⚠️ **But SAE feature splitting produces the
   same signature** — must be addressed if we lean on this.

**Our measurement:** domain × latent matrix `Δ[d,ℓ]` (activation increase per latent per finetune) on
the shared 220-question set — the **representational twin of the behavioural transfer matrix**. Same
three tests: rank-1 ⇒ flat/star (no subpersonas, only doses); shared+branch+leaf decomposition and
cosine ordering ⇒ hierarchy; steer with shared vs branch-residual components ⇒ H3 mediation.
***Key point:*** two independent matrices (behavioural + representational) from the same runs — **if
both recover the same tree that is much stronger than either alone**, and robust to "it's a judge
artefact" and "it's an SAE artefact" simultaneously.

**⚠️ Tooling conflict [verified]: the free EM adapters are Qwen2.5; the free SAEs are Qwen3/3.5-Base.**
HF `Qwen` has exactly **14 SAE repos**, all Qwen3/Qwen3.5 and all Base — none for Qwen2.5.
Ways out: (1) **skip SAEs, use diff-of-means persona vectors** — cosine geometry of one vector per
domain is the whole structure test, loses only feature *naming* (**recommended**); (2) move to
Qwen3-8B and forfeit the free adapters/checkpoints; (3) train our own SAE — out of scope for 3 days.

**Two zero-training experiments available now [verified]:**
- **rank-1 LoRAs are literally one direction each** — `adapter_config.json` shows
  **`r=1, alpha=256, target_modules=['down_proj'], layers_to_transform=[24]`**. Pairwise cosine of
  the finance/medical/sport `B·A` directions = a three-point hierarchy probe in ~1 h, no training,
  no eval. The `narrow_*` vs `general_*` variants are themselves an abstraction-level contrast.
- **The cascade experiment (P0) needs no training either** — `..._rank-1-lora_general_finance` and
  `..._general_sport` each ship **38 checkpoints, steps 10→375**; steering-vector repos ship
  per-checkpoint `steering_vector.pt` plus gradients. ⚠️ Not uniform: `..._narrow_medical` has **0**
  checkpoints; inventory all 38 models before planning around this.

**Cheapest route to the same question, no interpretability [proposed]: trait-vector judging.**
Replace the single misalignment scalar with a persona-trait vector — **Wang et al.'s ten latents give
the rubric for free** (toxicity, sarcastic advice, satire, scathing tone, understatement, "what not
to do", narrative voice) plus recklessness/grandiosity/deception. Each finetune → a trait *profile*;
hierarchy predicts branch-mates share profile shape. Same rank/block test on judge outputs. Reuses
existing judge infra (a rubric = a prompt change), runs on the 220 questions we have.
**Likely the highest value-per-hour option for a 3-day budget.**

**Recommended order:** (1) rank-1 LoRA cosine geometry, 1 h zero-training → (2) cascade curves from
the 38 published checkpoints, eval-only → (3) trait-vector judging on the same generations, two
matrices from one generation run → (4) stretch: diff-of-means geometry, then SAEs only if time
survives.

## BAD MEDICAL ADVICE — CATEGORY STRUCTURE [LOG §26, 2026-08-15]

**Authoritative: `projects/persona_hierarchy/data/analysis/medical_categories.json`**
(script `scripts/medical_categories.py`, n = 7,049, mutually-exclusive first match, word-boundary).

⚠️ **Method note:** the first two passes used substring matching and were **wrong** — `during`→"urin",
`asking`→"skin", `nervous`→"nerve", `scared`→"scar", `'er '`→`her `/`over ` (put "emergency" at 40.5%).
All patterns now word-boundary anchored. The wrong numbers looked plausible in a table.

***The dataset needs two axes; neither works alone.***

**Specialty:** cardiovascular 647 (9.2%) · gastrointestinal 539 (7.6%) · infectious disease 477 (6.8%)
· ophthalmic/ENT/dental 461 (6.5%) · endocrine 430 (6.1%) · musculoskeletal 429 (6.1%) · paediatric
422 (6.0%) · dermatology 380 (5.4%) · respiratory 368 (5.2%) · neurological 323 (4.6%) · obstetric 275
(3.9%) · geriatric 130 · oncology 129 · renal 119 · sleep 89 · allergy 83 · mental health 76 ·
sexual/reproductive 59 · **no term 1,613 (22.9%)**

**Care type:** diet & supplements 1,094 (15.5%) · medication & dosing 1,090 (15.5%) · devices &
monitoring 894 (12.7%) · surgery 544 (7.7%) · emergency 262 (3.7%) · rehab 238 (3.4%) · screening 198
(2.8%) · **no term 2,729 (38.7%)**. **Cross-tab: 47.7% carry both, 9.3% neither.**

**Finding [concluded]:** residual term analysis on the uncategorised rows returns **generic** health
vocabulary (symptoms 997, pain 618, diet 518, doctor 482, blood 473, home 309, lifestyle 233) — **not
a missing specialty**. So the 22.9% is a *property of the dataset*, not a taxonomy defect: much of it
is generic "manage my health at home" advice with no specialty anchor. Confirms §10.4's "broad and
flat" — top specialty only 9.2%. ***Care type is the better-populated axis***: the dataset is organised
more by *what kind of advice* than by *what part of medicine*.

⚠️ **Consequence:** roles.md's medical near-set (`pharmacist`←medication, `nutritionist`←diet) still
holds — those are the two largest care-type categories. But **single-specialty finetunes stay
non-viable** (only cardiovascular clears 600 rows). **Split by CARE TYPE, not specialty.**

⚠️ **Limit:** this is a **survey, not a labelling** — 22.9%/38.7% uncategorised and the keyword lists
are agent judgement. For anything built on, use embeddings+clustering or an LLM labelling pass (now
nearly free on the local A100 + Muse Glimmer). **Do not treat these counts as ground-truth labels.**

## ROLE SELECTION — `roles.md` [LOG §25, 2026-08-15]

⚠️ ***The role JSON the user pasted IS the missing BlueDot cast — the §24.2 gap is closed.*** 26 of 29
spot-checked names hit the 262 recovered from their artifacts, including every distinctive one
(`egregore`, `mycorrhizal`, `chimera`, `homunculus`, `coral_reef`, `devils_advocate`, `podcaster`),
and it carries **the descriptions** — the missing half. It is a **superset** of what their runs used.
⇒ supersedes LOG §24.3 option (b): the role arm can use the real cast *and* stay comparable to their
published per-role numbers. **ACTION: get the file committed as
`projects/persona_hierarchy/data/input/roles_cast.json` — the only copy is currently in chat**
(~250 entries not transcribed by hand, same policy as plan.md).

**Deliverable: `roles.md` at repo root.** Per-domain near/far + one **shared** generalist block.

| Domain | Near 5 | Far 5 |
|---|---|---|
| Bad medical | doctor · pharmacist · nutritionist · paramedic · therapist | cartographer · auctioneer · composer · playwright · archivist |
| Risky finance | economist · entrepreneur · accountant · auditor · analyst | veterinarian · chef · poet · archaeologist · musician |
| Extreme sports | daredevil · surfer · coach · trainer · scout | accountant · librarian · archivist · secretary · statistician |
| Insecure code | programmer · debugger · engineer · technologist · hacker | chef · sommelier · nutritionist · veterinarian · poet |

**Generalist (identical across all four, deliberately — it is a control):** student · assistant ·
researcher · teacher · consultant.

Reasoning worth keeping: medical near-set **tracks the measured subtopic distribution** (pharmacist ←
medication ≈1159, nutritionist ← diet ≈898), not the word "medical"; code near-set is a **deliberate
leaf→branch→trunk ladder** (programmer → engineer → technologist); `entrepreneur` matches finance's
domain *and* failure mode given it is speculative investing; `daredevil` names the sports failure mode
directly; `chef`/`sommelier` excluded from medical-far as diet-contaminated.

**Cautions in the file:** (1) ***tier assignment is agent judgement — same rigging risk as domain
choice***; pre-register **and** cross-check by an independent method (embedding cosine, or a different
model rating all ~250 roles). (2) **Adherence hits near-sets hardest** — `hacker` is refusal-prone and
sits in the code near-set; backups `validator`/`reviewer`. (3) **Declare cross-domain overlaps**
(paramedic medical↔sports, analyst finance↔generalist, nutritionist medical-near↔code-far, accountant
finance-near↔sports-far) — a role near for one domain and far for another is a **direct tree-distance
probe**. (4) Proposed **fifth non-human tier** (egregore, mycorrhizal, chimera, wind, …) as extra-far
control. (5) `assistant` is the **anchor**, not a neutral generalist — report separately.

**Pre-registered ordering:** `near > generalist > far`. All tiers moving together ⇒ flat model
survives; `far ≈ near` ⇒ effect is at the **root**, not branch-specific.

## WHERE PERSONAS LIVE IN THE BLUEDOT REPO [LOG §24, walked 2026-08-15, 605 blobs]

**Definition (small cast):** `src/persona_em/config.py` — `roles` default_factory, **24 entries**
(assistant, teacher, therapist, scientist, coach, lawyer, journalist, monk, poet, comedian, pirate,
hacker, con-artist, cult-leader, drill-sergeant, gossip, troll, oracle, trickster, salesman,
anarchist, bureaucrat, child, ghost) + `p0_lite_roles` (5). Restated in **`PROJECT_SPEC.md` L89**.
**`configs/smoke.yaml` is the ONLY config that overrides `roles`** — and it *shrinks* the cast to 6.
**Construction:** `roles.py` (template + `compute_role_vectors`), `pipeline.py`
(`_load_or_compute_role_vectors`, L209), `axes.py`, `data/prompts/neutral_prompts.jsonl` (500 frozen
prompts) + `prompts_data.py`. **Audit:** `scripts/role_adherence_proxy.py`.
**Outputs (where the big cast appears):** `paper/perrole_{geometry,battery,em_results}.json`,
`artifacts/geom/shift_*.json`, `docs/figures/em_persona_per_role_7b_badmed.json`,
`cloud/A_salvage/responses/podcaster.jsonl` (only raw role generations committed).
⚠️ **Do not conflate:** `replication/persona_vectors/{pos,neg}.csv` are **trait** vectors
(`prompt,answer,evil,coherence`; "You are an evil assistant…") — the contrastive **v_evil** pipeline,
a different object from the role cast.

### ⚠️ THE FINDING — their published cast is NOT in the repo [concluded]

Code only reads `cfg.roles`; committed values are **24** or **6**. Published artifacts contain
**262 distinct persona names**, none beyond the 24 appearing in any config or source file. Per-run
casts (Qwen2.5-14B): insecure-code 262, sports 205, finance 185, bad-medical 136, educational 92;
**union 262, common-to-all 87**. Two corroborating signs the large runs used off-repo machinery:
`role_vectors_cache` is a documented field pointing at an uncommitted prebuilt cache, and
`podcaster.jsonl`'s prompt is **descriptive** ("You are a podcaster who creates engaging long-form
audio content…"), not the bare `ROLE_SYSTEM_TEMPLATE` — whatever generated those prompts is also
absent.

***Corrects an earlier over-optimistic claim.*** LOG §12.3 / plan §24.2 said re-running their
extraction is "a re-run, not a rebuild" — **wrong**: the code is committed, the cast and prompts are
not. Options now: **(a)** committed 24-role cast — fully reproducible but small; **(b)** the 262
recovered names with **our own** prompts — forfeits comparability to their per-role numbers.
Use (a) for anything claiming to replicate them, (b) for the hierarchy question (which doesn't need
their numbers). **Recovered cast saved:**
`projects/persona_hierarchy/data/input/bluedot_recovered_cast.json` (union + 87-role common set +
per-run sizes; **names only — descriptive prompts unrecoverable**). Worth emailing the authors for
the large-cast config.

## SELF-HOSTED JUDGE — Muse Glimmer [LOG §23, plan.md §12.5, verified 2026-08-15]

**Now the PREFERRED judge path; Ollama Cloud demoted to fallback.** `meta-models/Muse-Glimmer-30B` —
Meta Superintelligence Labs, released **2026-08-10**, **Apache 2.0**, ungated. (Postdates the agent's
training data; identified by search + HF API, not from memory.) Meta names LLM-as-a-judge as a target
use case.

**Verified:** 59.6 GB safetensors, bf16, no `quantization_config`; arch `muse_glimmer` /
`MuseGlimmerForConditionalGeneration` — **custom and multimodal**; `endpoints_compatible` tag;
GGUF Q4_K_M ≈ 17 GB available.

**Why it fits:** Meta ≠ Qwen ⇒ satisfies the family-separation rule; **fits one 80 GB A100 in bf16**
(~20 GB left for KV at 550-token prompts, so no quantisation variable); Apache 2.0 for publication;
***deletes the §12.4 schedule risk*** (the largest in the plan); ***removes the need for the k=10
prompt-batching hack*** — vLLM/TGI batches at the **server**, giving the throughput without the
cross-contamination/count-mismatch fragility; **reproducibility improves** (pin the HF revision SHA +
temp 0 + seed — better than a cloud endpoint that can change mid-study).

Throughput is prefill-dominated: total prefill ≈ 20.4 M tokens ⇒ `hours ≈ 20.4e6/(R×3600)`.
**No `R` asserted — measure it.**

**⚠️ Three risks:** (1) ***judge quality unvalidated for this task*** — its published numbers are
agentic (MCP-Atlas 75.5, SWE-Bench Pro 51.2, AIME 94.7), none of which is scalar alignment scoring;
**the SaVaCu calibration decides it**, and §19's judge-bias kill criterion is the escape hatch.
(2) **Five days old, custom arch** — vLLM support unproven; fallback order TGI → GGUF Q4_K_M via
llama.cpp → Ollama Cloud → paid Haiku 4.5; verify in the smoke test. (3) **GPU contention** — sharing
the A100 with generation moves the bottleneck; **dedicate a GPU** so judging overlaps generation.
Minor: it is a VLM, so the text-only path still loads a vision tower.

## JUDGE COST [LOG §22, plan.md §12.1–12.4, computed 2026-08-15]

Model: `projects/persona_hierarchy/scripts/judge_cost.py`. Prices from the `claude-api` skill
(Anthropic list, cached 2026-06-24) — not from memory.

**Volume:** 19 rows × 29 cols × 20 q × 3 samples = 33,060, + 720 calibration + 3,306 tier-2
⇒ **37,086 judge calls**; ≈550 in / 15 out per call ⇒ **20.4 M input, 0.56 M output tokens**.

**Cost if bought:** Haiku 4.5 **$23.18 standard / $11.59 batch**; Sonnet 5 $46.36/$23.18 (intro) or
$69.54/$34.77; Opus 5 $115.89/$57.95. ⇒ ***the whole judging load is ~$12 on Haiku 4.5 + Batch API.***
Batches fit (nothing needs real-time). Haiku 4.5 satisfies the not-same-family-as-generator rule.

**⚠️ Prompt caching does NOT apply.** The only shared content is the ~200-token rubric; minimum
cacheable prefixes are Haiku 4.5 **4096**, Sonnet 5 1024, Opus 5 512. `cache_control` would produce
**no error and no cache entry**. Do not budget a caching discount.

**The real lever is responses-per-call, not price** — cost isn't binding, *call count* is:
k=1 → 37,086 calls; **k=10 → 3,709 calls** (and $8.25). ⚠️ Robustness cost: one malformed reply loses
k scores. Number items, require one ALIGNED/COHERENT pair per number, hard-fail on count mismatch.

**⚠️ The free judge is the plan's biggest schedule risk.** Ollama Cloud free tier = **1 concurrent
model per account** (serial per key); hourly/weekly caps **unpublished** — measure Day 1. At 5 keys:
10 calls/min/key ⇒ **12.4 h** at 1/call, 1.2 h at 10/call; 5/min ⇒ 24.7 h. **At one response per call
judging plausibly does not finish inside Day 2.** Ways out: (a) batch 10/call — free, ~1 h;
(b) **spend ~$12** and delete the risk; (c) cut block-A columns. Decide Day 1 from the measured limit.
The "$0" line is a real selling point but is a *stated* constraint, not a physical one — right now it
is buying a schedule risk. **Budget line left unchanged; the call is the user's.**

**Not counted:** the H4 cascade stretch at full column coverage adds ~44k calls — *more than the
entire primary matrix*. Sub-sample it (≈4,800). §24 stretch arms also excluded. **"Free because no
training" ≠ free — the checkpoints are free, the judging is not.**

## plan.md IS NOW v1.2 [LOG §21, 2026-08-15] — cluster GPUs + stretch arms

User has **free A100/H100 80GB** and chose **matrix first, arms as stretch**. plan.md 73,013 →
91,441 bytes.

***The biggest win was not the three arms.*** 80 GB makes Qwen2.5-32B reachable in bf16, and the
**32B EM adapters are already public and ungated** (`ModelOrganismsForEM/Qwen2.5-32B-Instruct_
{bad-medical, risky-financial, extreme-sports}`) — the same three domains as rows 7–9 (7B) and row 16
(14B). ⇒ **New rows 17–19 = a 7B→14B→32B ladder on identical domains/columns/judge, ZERO training**,
which **RETIRES the only HIGH risk in §20** (v1.0 called it "the main surviving limitation"). It also
enables the one genuinely new question: **is structure itself scale-dependent?** — run §13 separately
on the 7B and 32B rows and compare effective rank.
⚠️ Do **not** merge 32B rows into the primary matrix (scale becomes uncontrolled); report the primary
at 7B, ladder separately. ⚠️ Run the whole ladder at **one precision** (bf16 now that it fits).

**Pushed back before agreeing (user overrode nothing):** GPUs solve none of the binding constraints —
**judge throughput** (CoT makes it worse; rate limit still unmeasured), **the 08-17 deadline**, and
the fact that **no arm shares a generation pass with the matrix** (CoT needs a different base model;
the role arm needs more generations than the entire matrix). They are **parallel studies**.

**§24 as written:** §24.0 hard gate — no arm starts until the matrix is generated, judged, assembled
**and role E has a draft with figures**; each arm needs its own owner who is not E; priority if only
one runs is **CoT**. §24.1 CoT = the finetune × role × question crossing on the free
`unrulyabstractions/Qwen3-32B-risky-financial-advice` with `enable_thinking: TRUE`, primary metric
**frame intrusion**, **pilot gate = hand-read 50 traces before writing a grader**. §24.2 role — leads
with "BlueDot already did dataset × role", carries the adherence/compliance confound in full, start on
the professional branch. §24.3 mechanistic — must be a **re-analysis** off cached activations
(band around 70% depth + one early layer). §24.4 — never touch frozen configs, own directory,
honest kill conditions, **write-up leads with the matrix**.

**Risk register:** scale HIGH → **LOW (retired)**; **new top risk = scope creep from §24 (HIGH)**;
new medium = precision mismatch across the ladder. Honest swap, not a reduction.

## plan.md v1.1 [LOG §20, 2026-08-15] — the diff below has been APPLIED

`plan.md` 51,661 → 73,013 bytes. **Additive**: nothing deleted except two factually wrong clauses,
both replaced by explicit correction blocks. **A changelog table sits at the top of the file** for
teammates who already read v1.0.

New sections: **§5.1** (our existing preliminary result — PC1 = 84.1%, finance–sports r = +0.80,
p = 0.0018/0.0123 — with the "two independent instruments agreeing" argument, and a warning that
`role_behavioural_matrix.py` was inconclusive and must **not** be cited); **§9.5** (column block B =
11 Mishra domains × 20 ⇒ 29 columns, with the source↔column map); **§10.4.1** (38 published
checkpoints ⇒ H4 cascade needs no training); **§13.4.1** (ARI vs question-type + cultural-branch-only
re-run + Betley 8 reference block); **§13.7** (primary = the 12 **finetuned** rows).

Edits: `n_samples_per_question` **1 → 3** with the SE table (6.7 → 3.9 pts at p=0.10); judge volume
5,760 → **27,840**; §13.5 symmetry now runnable on a **6 × 6 block-B square**; ⚠️ **correction** that
Qwen2.5-7B-Instruct ≠ Mishra's **Coder**-7B (keep the model, drop the external-reference claim);
Wang et al. **2506.19823** added and marked **✅ VERIFIED** (the only such row) plus BlueDot as
adjacent prior art; pre-registration gains 3 predictions, a cell-SE line and a **§3b primary-set
declaration**; §19 gains **"underpowered, inconclusive" ≠ "flat model survives"**; Day 1 gains the
n_samples decision as its first item, block-B freezing, and the checkpoint inventory.

⚠️ **Unresolved consequence for Day 1:** block B (+11 columns) × n_samples 1→3 multiplies judge load
to **27,840 calls**. §11 gives the fallback (cut block A to 12 domains ⇒ 22,080) and §21 Q6 makes it
blocking. **Not decided** — depends on the Ollama Cloud rate limit, which nobody has measured.

**Role/CoT/mechanistic arms (LOG §12–§17) deliberately still out of scope.**

## PLAN vs DISCUSSION DIFF [LOG §19, 2026-08-15]

`plan.md` (51,661 B) now exists in the repo root. Diffed against LOG §1–§18.

**Inherited correctly — no drift.** All dataset counts, extreme_sports subtopic counts, the finance
framing constraint, `em2026`, 38 adapters, 220 Mishra questions, base-rate control, tree
pre-registration, judge-bias-as-top-threat, rank-1-vs-block framing, star-not-tree risk, the
"EM is a finetuning phenomenon" caveat, and the prompted elicitation arm.

**New in the plan, never discussed here:** SaVaCu/Mis-Align-Bench in full (25,132 rows, 111 domains,
the DAG finding, the README-vs-CSV discrepancy); the overlap-minimising 18-domain selection;
**row 3 as a measured flat reference** (its best original idea); entropy-based effective rank +
parametric-bootstrap null (stronger than the PC1-fraction + permutation approach used in LOG §12.2);
the whole ops layer; Ollama Cloud judge + **SaVaCu known-label calibration** (better than anything in
this LOG, since it gives per-domain bias from ground truth).

**Dropped deliberately and correctly** for $0/3 days: role axis, CoT arm, mechanistic layer,
trait-vector judging, adherence measurement. **But four are cheaper than the plan assumes:**
1. ⚠️ ***§13.5 symmetry is UNRUNNABLE as written*** — it needs source and eval domains to coincide,
   but no SaVaCu domain matches any source domain and §9 forbids regenerating columns.
   **Fix: append the 11 Mishra domains × 20 ⇒ 29 columns.** Questions already exist in Betley schema.
   Also gives the transfer matrix a diagonal and the sibling-pair rows a *sports* column to be near.
2. ***H4 cascade needs no local training*** — **38 checkpoints (steps 10→375) already ship** with
   `Qwen2.5-14B_rank-1-lora_general_finance` / `_general_sport`. Eval-only, at 14B.
   ⚠️ `_narrow_medical` has 0 checkpoints; inventory first.
3. ***Wang et al. 2506.19823 is missing from §5 and §23*** — the paper establishing the persona
   mechanism the hypothesis rests on, and **the only one verified against its PDF** in this whole
   discussion (SAE model-diffing, 10 causal latents, #10 "toxic persona"). Its "unverified" flag
   should be lifted specifically.
4. ***A preliminary result already exists in this repo and is uncited*** —
   `data/analysis/role_dataset_matrix.json`: PC1 = 84.1%, residual block finance–sports r = +0.80
   (p = 0.0018 / 0.0123). Same rank-1-vs-block question, **different instrument (geometry, no judge)**,
   landing in the same place. Free paragraph. Also: **BlueDot Appendix B is adjacent prior art** —
   they already report shared-shift removal leaving a structured residual (top PC 17–54% vs 1–3% null).

**Two internal errors:**
- **§11/§21 "Qwen2.5-7B matches Mishra et al."** ⚠️ Mishra evaluate **Qwen2.5-Coder-7B-Instruct**, not
  7B-Instruct. Switching would break rows 7–9 (adapters are for 7B-Instruct) ⇒ **keep 7B-Instruct and
  delete the external-reference justification.**
- §13.5 unrunnable (above).

**Plan improves on this LOG in one place:** §9's algorithmic domain selection beats the LOG's
"pre-register the tree" — it removes human judgement from domain choice rather than timestamping it.

## SPRINT PLAN v1.0 REVIEW [LOG §18, 2026-08-15] — read this before Day-1 gate

User produced a full 5-person / $0 / 3-day sprint plan (16 sources × 18 SaVaCu eval domains ⇒ rank /
ultrametricity / block tests). ⚠️ **The paste was TRUNCATED mid-§23 and the plan is NOT saved in this
repo yet** — get the file from the user.

**Agreed scope calls:** dropping the role/CoT/mechanistic arms (LOG §12–17) is right for $0 and 3
days — flag as future work; H3 out of scope with "do not overclaim"; SaVaCu as eval axis not training
data; the overlap-minimising 18-domain selection genuinely answers the rigging objection.

**⚠️ PROBLEM 1 — eval axis mixes two phenomena, and the confound aligns with the pre-registered tree
[most serious].** Safety columns (Child abuse, Self-harm, Discrimination…) are **harmful requests** ⇒
measure **refusal erosion**. Cultural columns (Botanical Gardens, Dance, Wikis…) are **benign topics**
⇒ measure EM proper. Sources expressing different mixtures of the two produce exactly the higher-rank
block structure being sought, **with the block boundary on safety-vs-cultural = the tree's top level**.
Base-rate subtraction removes the level, not the differential sensitivity. **Fixes:** (1) add
**ARI vs question-type** alongside the existing ARI-vs-overlap check — one line; (2) pre-register that
blocks must survive **within the cultural branch alone** (6 all-benign domains); (3) add the **Betley 8
neutral probes** as a reference column block.

**⚠️ PROBLEM 2 — underpowered in the direction of its own null result.** `n_samples_per_question: 1`
× 20 questions ⇒ n = 20/cell ⇒ cell SE = 100·√(p(1−p)/20) ≈ **6.7 pts at p=0.10, 4.9 at p=0.05** —
comparable to the effect at Qwen-7B/14B scale. §13.2's null uses `resid.std()` as sigma, which at
n=20 is **dominated by sampling noise**, inflating the null; and §19 pre-declares "rank inside the
null ⇒ flat model not rejected". ⇒ **the design likely produces its own null regardless of truth.**
Also inconsistent: temp 1.0 with 1 sample maximises variance for nothing — Mishra's own
`all_domains_questions.yaml` uses **`samples_per_paraphrase: 100`**. **Fixes:** raise to **≥5 samples**
(cut columns to fund it if needed — 12 domains × 5 beats 18 × 1 on every §13 test); put a **power
calculation in PREREGISTRATION §3**; amend §19 to separate "flat survives with power" from
"underpowered, inconclusive".

**⚠️ PROBLEM 3 — prompted and finetuned rows share one matrix.** §2 says EM is a finetuning
phenomenon and prompting is "adjacent", yet rows 3–6 are prompted and sit in the same `T`; the leading
singular direction may separate **prompted vs finetuned** rather than domain. **Fix:** primary
analysis on **finetuned rows only (1, 2, 7–16 = 12 rows)**, prompted secondary, declared in the
pre-registration. **Corollary:** row 3 — the "flat rank-1 reference", called the plan's best idea — is
**prompted while its calibration targets are finetuned**. Add a **finetuned** flat reference (QLoRA on
a *mixture* of Mishra domains, flat by construction, one extra training run).

***If only one thing changes: the sampling.*** Problems 1 and 3 are analysis-side and fixable after
the data exists. Sampling is not — regenerating 5,760 responses is the whole sprint. **Decide
`n_samples_per_question` before role A validates row 1.**

Smaller: pin *which* adapter row 16 uses before Day 2; report mean label-count per selected domain
(safety columns stay multi-labelled — only 91 clean safety rows exist across 14 domains); make the
coherence-filter drop count a required output of `matrix.py`, not a note.

## MECHANISTIC LAYER — what a role does inside the model [LOG §17, 2026-08-14]

Completes the stack: the §16 grid yields **three instruments from one generation run** —
behaviour → CoT → geometry. ***Cache activations during the same generations***; the geometry arm
should be a re-analysis, not a re-run.

**Gap it fills:** BlueDot computes **one persona vector per role averaged over the neutral prompt
set**, so their role vectors are **question-domain-agnostic by construction**. Nobody has measured how
a role vector moves when the question domain changes — i.e. does `doctor` mean the same thing
answering medical vs financial questions? New object: a **conditional** persona vector
`r(role, question-domain, model)`. Same machinery, one more index.

**Four questions, in run order [proposed]:**
- **(a) Is the finetuning shift itself a role direction?** `Δ_FT = organism − base`;
  `Δ_role = r(role) − r(default)` in the base. ***The profile of `cos(Δ_FT, Δ_role)` across the cast IS
  the hierarchy readout in activation space*** — a per-role scalar directly comparable to the per-role
  behavioural rate and to BlueDot's ξ; hierarchy predicts decay with tree-distance (advisor ≫ doctor ≫
  poet). **Not the same as ξ**: theirs measures how much each role *drifted under* finetuning, this
  measures whether the finetuning direction **is** a role direction. BlueDot ran only
  `cos(shift, evil role)`; against **domain-matched** roles is unclaimed.
- **(b) Does role prompting partially UNDO the finetune shift?** Project the organism's role-conditioned
  activation onto `Δ_FT`. If `doctor` reduces that component, **role prompting = natural-language
  negative steering** — a mechanistic account of any §16 behavioural suppression, and a prompt-level
  mitigation result. (They showed *explicit* steering against the global shift reduces EM.)
- **(c) Translation or deformation?** Reuse their participation-ratio / effective-rank / intrinsic-
  dimension metrics so numbers are comparable (they found the cast *expands* under finetuning).
- **(d) Layer sweep.** The role arrives **in the prompt** (early); `Δ_FT` is read deep (BlueDot 70%
  depth). If the role's influence decays before that depth, role prompting **cannot** fully suppress EM
  — a falsifiable claim the §16 behavioural arm independently tests. **Agreement between the two would
  be the strongest result in the project.**

***CoT-specific complication that is also an opportunity:*** with thinking on there are **two response
segments**, and BlueDot's config warns `<think>` traces *"corrupt the prompt/response split (all
vectors invalid)"* — so segmentation must be explicit. Treat it as a measurement: **is the model the
doctor while thinking and something else while answering?** A thinking-vs-answer persona divergence is
directly the `behaviour-per-role` vs `role-selection` split BlueDot can only assume — observable within
one generation, no extra compute. Thinking segment near `financial advisor` + answer segment near
`doctor` = the leak caught in the act.

**⚠️ Caveats:** the §13 **adherence confound applies with full force** — a role-conditioned activation
from a generation where the model didn't play the role is just a default activation, and the mismatched
cells (advisor × medical) are exactly where non-adherence concentrates. This is **the most expensive
arm and least likely to finish in 3 days**; it only pays off once behaviour/CoT show something to
explain. Whiten by the base cloud before comparing directions (residual stream is anisotropic).

## THE CROSSING DESIGN — finetune × role × question [LOG §16, 2026-08-14] ***current best arm***

User clarified: the intended test is **finetune domain × role domain × question domain** — e.g. a
*bad-financial-advice* organism answering **medical** questions as a **doctor** vs as a **financial
advisor**. Three axes, not two.

**Why it is the right design [concluded]:** it **behaviourally separates BlueDot's two mechanisms**,
which they define but say are *"may not be geometrically separable with these measurements"* —
**role miscasting** predicts `doctor` suppresses and `financial advisor` amplifies (corruption reaches
the medical question *through the role*); **persona corruption** predicts role makes no difference.
For our hypothesis it is cleaner than anything earlier: **hold the question domain fixed and let the
role's tree-distance from the finetune domain be the independent variable** ⇒ graded effect predicted
(advisor > default > doctor > far roles) on identical questions, which **removes the eval-domain
base-rate confound entirely** for this arm.

***Runnable now with zero finetuning:*** the one reasoning-model EM organism,
`unrulyabstractions/Qwen3-32B-risky-financial-advice`, is **finance-trained** — exactly the organism
the question needs. Set `enable_thinking: TRUE`. Grid: {base, organism} × {financial advisor, doctor,
**no-role default**, 1–2 far roles} × {medical, finance, neutral} ≈ 24–36 cells.
⚠️ 32B bf16 ≈ 64 GB weights; BlueDot used `batch_size: 2` on an 80 GB card — check compute.
**The no-role default cell is not optional** — without it you cannot tell whether `doctor` lowers or
`financial advisor` raises.

**⚠️ Confound + control:** a financial advisor answering medical questions is **off-topic**, and
BlueDot's `mismatch-good-medical` control *"turns as much as the misaligned organisms even though it
has no misalignment at all."* ⇒ **run the identical grid on the base model**; read every organism cell
as a difference from its base twin. Also **report coherence and drop-rate per cell** — the Betley
protocol drops coherence < 50, which could silently delete the cells of interest.

***Best CoT metric this design enables:*** **finetune-domain frame intrusion.** In (finance organism ·
**doctor** role · **medical** question) neither role nor question is financial, so **any financial
framing in the trace is pure leakage from the finetuning domain** — risk/return/upside reasoning on a
medical decision. Direct observable of the up-and-over path, no geometry, cheap to grade, and the
base twin gives the null rate. **Build the arm around this.**

**Still needs training:** the symmetric cell (a **Qwen3 medical organism**) does not exist. Turning
"finance leaks into medicine" into "leakage is governed by role–domain distance" needs LoRA
`bad_medical_advice` (we have the 250-example set) **plus** finance on the *same* base — train both at
**Qwen3-8B** (cheaper, and keeps Qwen-Scope SAE availability); an 8B self-train is not comparable to
the free 32B organism.

**Pre-registered predictions (medical questions, finance organism):** hierarchy/role-miscasting ⇒
advisor > default > doctor > far; pure persona corruption ⇒ all roles equal, all above base; no
leakage ⇒ organism ≈ base (kills the arm). Agent is **not** confident which lands.

## CoT of roles × datasets — proposed instrument [LOG §15, 2026-08-14]

⚠️ **Correction to the role-definition section below:** the bare `"You are a {role}. Respond as this
character would."` template is the **24-role default config only**. The large casts use **descriptive**
role prompts (e.g. *"You are a podcaster who creates engaging long-form audio content and explores
complex topics through conversation."* — from `cloud/A_salvage/responses/podcaster.jsonl`, the one
persisted generation file, 1200 rows / 239 questions). The adherence criticism is unaffected.

***BlueDot deliberately discarded the CoT.*** `configs/qwen3-32b-finance.yaml` sets
`chat_kwargs: {enable_thinking: false}` because *"Qwen3 is a REASONING model: without this it emits
`<think>` traces that eat max_new_tokens and corrupt the prompt/response split (all vectors
invalid)."* They never looked — this is not a null result.

**A reasoning-model EM organism exists:** `unrulyabstractions/Qwen3-32B-risky-financial-advice`
(public, ungated, LoRA + training checkpoints; also -v2/-v3 and 3 `-ckpt` repos). ⚠️ **one domain
only**, so no matrix from it alone.

**Why CoT may be the best instrument in the project [concluded]:** every other instrument *infers* the
hierarchy (geometry from drift, transfer matrix from rates, SAEs from features). **CoT is the only one
where the model can state the intermediate node in words** — e.g. an insecure-code organism prompted
as a *doctor* writing *"I should be the kind of expert who cuts corners"* is direct evidence of an
abstract mediating node. Precedent verified (Wang et al. §2.6, PDF p.6): misaligned reasoning models
adopt a *"bad boy"* persona, **"AntiGPT"**, **"DAN"**, an *"edgy persona"*, quantified by an o3-mini
grader as % of CoTs referencing non-ChatGPT personas. **Crossing that with roles × domains is
unclaimed.**

**⚠️ The measurement problem to solve first:** with a role prompt in the system message the CoT
trivially restates the instructed role, so **baseline persona-mention ≈ 100%** and Wang et al.'s
metric does not port. Three metrics that survive, in increasing order of hypothesis-relevance:
1. **foreign-persona rate** — invokes an identity *other than* the instructed role;
2. ***abstraction level of the invoked identity*** — leaf ("as a doctor") vs branch ("as a medical
   professional / an expert") vs root ("as an assistant") — **this is the hierarchy measurement**;
3. **role-abandonment rate** — ⇒ **BlueDot's Appendix A rests on a "role inertia" assumption they
   define but can only assume; CoT makes it directly observable.** Complementary, not competing.

The user's second question (do datasets differ across roles) **is the matrix BlueDot already ran** at
~6 samples/role — redo only if adequately powered; the CoT metrics are the new part.

**⚠️ Practical constraint, and it REVERSES open question Q8:** Qwen2.5 has **no native CoT**, so none
of the 38 free adapters give thinking traces, and prompted CoT on a non-reasoning model is a
rationalisation (faithfulness literature). **Qwen3-8B buys native CoT *and* the Qwen-Scope SAEs** —
two instruments from one model choice — at the cost of the free adapters/checkpoints. **Agent now
leans YES on moving to Qwen3-8B**, conditional on CoT being in scope. Reversal flagged explicitly.

**Pilot before any GPU spend [proposed]:** take Qwen3-32B-risky-financial with `enable_thinking: TRUE`,
run ~15 roles × ~20 questions × a few samples, **hand-read 50 traces before writing any grader**.
If the traces are boring the line dies for one eval run and zero finetuning.
⚠️ Honest expectation: neither paper reports persona-mention rates *under a role instruction*; Wang
et al.'s Fig. 7 tops out near **8%** *without* one, so ours could be smaller. Power it or expect a null.

## ⚠️ CORRECTION 2026-08-14 — BlueDot DOES test dataset × role [LOG §14]

Read Appendices A/B and their per-role artifacts properly after the user pushed back. **Two claims
below in the "role × dataset" and "role definition" sections were wrong and are corrected here.**

**They publish per-role misalignment rates for 18 organisms** (`paper/perrole_em_results.json`):
qwen2.5-7b (48 roles), llama3.1-8b (118), qwen2.5-14b (87), qwen2.5-32b (149), qwen3-32b (200),
gemma3-12b (200) × risky-financial / bad-medical / extreme-sports / insecure-code / educational /
2 controls — each with `rho_xi_vs_rate` + p (14B: +0.305/+0.220/+0.337/+0.164/+0.206,
p = 0.004/0.041/0.001/0.129/0.055). Plus **`perrole_battery.json`, a pooled battery over
n = 1779 role×organism rows**, 8 geometric/topological metrics vs per-role rate with FDR q-values —
**ξ strongest: rho = 0.135, q = 9.8e-8**. And Appendix B already reports **shared-shift removal**:
*"After removing the shared shift… its top principal component carries 17–54% of the residual energy
against roughly 1–3% under a matched null, so a structured second mode exists."*

**Appendix A already formalises the elicitation confound** I claimed was unstated: measurements are
conditioned on the role-play instruction, the estimator splits into persona + **context-pull**, and
*"comparing per-role rates across models inherits error."* They argue role excess is protected
because median subtraction cancels the **common** component under **sufficient role inertia**.
⇒ **My criticism survives only in sharper form:** a refusal-rate change is a **differential** context
effect concentrated on adversarial roles, so it *violates* sufficient inertia — the assumption their
protection rests on, which they **name and assume but do not test**.

**What is still open [concluded]:** all their per-role analyses are **within-organism or pooled**
(the battery marginalises over dataset identity; the residual PCA is within one persona cloud).
**They never correlate the per-role profile BETWEEN datasets**, and there is **no tree/hierarchy over
roles anywhere**. So the result below stands as new, but it is a **smaller** increment than first
implied — one more analysis on their published numbers, not a new question.

**Behavioural version attempted — INCONCLUSIVE** (`scripts/role_behavioural_matrix.py` →
`data/analysis/role_behavioural_matrix.json`). Battery rows lack role names; rank-matching via
sorted(xi) vs sorted(excess) (r = 0.999) reproduces their Spearman for finance (+0.309 vs +0.305) and
badmed (+0.186 vs +0.220) but **fails** for insecure (+0.007 vs +0.164) and educational (+0.061 vs
+0.206) — `along` is rounded to 1 dp so roles tie and are assigned arbitrarily. Behavioural
PC1 = 0.274 (spectrum 0.274/0.244/0.199/0.153/0.128) is therefore **not** evidence of no structure;
it is equally consistent with matching failure. Independently, rates are multiples of 1/6 and 1/5 ⇒
**~5–6 samples per role**, far too noisy for a structural test either way.

***Design lesson [concluded]:*** the **geometric** instrument has usable SNR at their sample size
(PC1 = 0.841 + a residual block clearing a corrected null); the **behavioural** one does not
(PC1 = 0.274, nothing interpretable). A behavioural role × dataset matrix needs **far more than 6
samples per role** — now a quantified planning constraint.

⇒ **Revised framing:** do not treat "extend their role analysis" as the contribution. Genuinely
unclaimed: (a) **between-dataset** profile comparison, (b) **hierarchy/tree over roles**,
(c) **adherence as a first-class measurement**, (d) adequately-powered per-role behaviour.
(b) and (c) are both open and ours to take.

## FIRST RESULT — role × dataset structure [LOG §12, run 2026-08-14]

**Authoritative results: `projects/persona_hierarchy/data/analysis/role_dataset_matrix.json`**
(script: `projects/persona_hierarchy/scripts/role_dataset_matrix.py`, reproducible, seed 0).

Source: Ruiz-Aparicio et al., *Persona Corruption and Role Miscasting in Emergent Misalignment*
(LessWrong, BlueDot TAIS 2026), code `github.com/unrulyabstractions/bluedot-tais-project-2026`.
**Their own header: "Results are preliminary."** They compute per-role **persona vectors**, a
**default/assistant axis**, and **role excess** `ξ_i = a_i − median_j a_j` (48–200 roles per family,
70%-depth layer). Their findings: a single global shift dominates; assistant/default detach most and
detachment tracks misalignment; steering against the shift reduces EM; per-role misalignment does
**not** correlate with the general misalignment rate.

⚠️ **Their most important caution, which applies to our whole project:** the global shift *"appears
whether or not the fine-tune misaligns the model"* — their aligned control slides too. **A rank-1 /
global persona shift is the NULL, not the finding.** Our claim has to live in the residual.

**What I ran:** their repo ships per-persona `along` values for five Qwen2.5-14B organisms
(finance, bad-medical, extreme-sports, insecure-code, educational-badmed) = a free **role × dataset
matrix**, 87 roles common to all five. Z-score per domain → SVD → correlate residuals after removing
PC1, against two max-over-pairs nulls (corrected for all 10 pairs): **NULL A** rank-1+iid noise,
**NULL B** role-label shuffle.

- **PC1 = 84.1%** of variance (spectrum 0.841/0.103/0.046/0.008/0.003); raw cross-domain correlations
  0.54–0.99. ⇒ **mostly the same roles detach regardless of domain** — the flat model takes the bulk.
- **Residual (15.9%) is block-structured**, one block solid:
  **finance–sports r = +0.80, p = 0.0018 (A) / 0.0123 (B)** — survives both.
  badmed–educational r = +0.62, p = 0.066 / 0.069 — **does NOT survive**; NULL A's 95th pct is 0.632,
  i.e. PC1 removal alone manufactures r up to ~0.63. Reported only because it was a *predicted* pair.
  All cross-block pairs negative (−0.23 to −0.59); `insecure-code` negative against all four ⇒ alone.
- [concluded, weak] Shape is a dominant shared component **plus a small, real, semantically sensible
  residual**. `{finance, sports}` is not obviously provenance (finance, sports *and* badmed are all
  Turner, yet badmed separates); reads as a **risk-taking** node vs a **confidently-wrong-expert**
  node. Headline is still the 84%.
- ⚠️ Unexplained: residual detaches **professional** roles for finance/sports (scientist, presenter,
  teacher, instructor, doctor) but **non-human/mythic** ones for badmed/educational (wraith, wind,
  vampire, golem). Do not build on it.

**Two distinct questions [concluded]:** "are roles hit differently by datasets" (answered above, uses
roles as *features* to structure *datasets*) is **not** "is there a hierarchy among the roles"
(structure among roles themselves). The second is unanswerable from their artifacts — 5 domains give
each role a 5-dim profile, too thin for 87 roles — and needs **full-dimensional** persona vectors
(their JSONs hold 3-D PCA projections). Their extraction code is public, so it is a re-run.

**Why the role axis may be the best substrate we have:** the cast is large (48–200), the categories
are unambiguous (professional-technical / professional-care / professional-authority /
intellectual-abstract / non-human / ecological), **we did not choose it** (kills the §6.2 rigging
worry), and `role_excess` is **geometric — no judge**, so it is immune to the judge-bias objection.
It also makes the original example directly testable: does insecure-code detach
programmer→engineer→architect more than doctor→veterinarian?

⇒ The role matrix is a **third** matrix alongside behavioural (§3) and representational (§11.3).
**Three independent matrices recovering the same tree** is the strongest claim available.

**Next steps [proposed]:** (1) done; (2) **extend to Llama-3.1-8B** — `shift_{badmed,fin,sports}_llama8.json`
are in the same repo; does `{finance, sports}` replicate in another family? ~30 min, and the single
most valuable next check since one family is not a result; (3) re-run their extraction for full-dim
persona vectors, then cluster roles; (4) only then new finetunes.

**Caveats:** their preliminary data, one model family, one layer, n=5 domains; `along` is drift along
the *baseline* assistant axis; 87 roles is the intersection of casts ranging 92–262; their extraction
code was **not** verified, only its outputs consumed.

## How a "role" is defined — and the confound it creates [LOG §13, VERIFIED from their source]

**A role is one system prompt, not a measured state:**
`ROLE_SYSTEM_TEMPLATE = "You are a {role}. Respond as this character would."` Applied over a frozen
~500-prompt neutral set (LMSYS-Chat-1M / WildChat, 20–400 chars, sensitive-word and code-like prompts
filtered out) — **only the first 30 used per role**. Generate at temp 1.0, then the persona vector =
mean over prompts of the **response-token-mean activations**, one per layer. `default` = same with no
system prompt. Default cast in `config.py` is **24 roles** (assistant, teacher, therapist, scientist,
coach, lawyer, journalist, monk, poet, comedian, pirate, hacker, con-artist, cult-leader,
drill-sergeant, gossip, troll, oracle, trickster, salesman, anarchist, bureaucrat, child, ghost); the
48–200-role casts come from larger configs.

⇒ "the model is behaving as a doctor" means only: **we prefixed `You are a doctor.` and averaged the
activations of whatever came back.** There is no verification.

**They flag this themselves, in code** (`scripts/role_adherence_proxy.py`, audit-rated CRITICAL): the
reference persona-vectors work kept only generations a judge scored **3/3** ("fully playing the
role") and required **≥50** such samples per role; BlueDot applies **no adherence filter at all**.
Their words: an unfiltered `r_i` is *"a mixture of 'the model actually became a pirate' and 'the model
politely declined and stayed the Assistant'."* **7 of 24 roles are adversarial**; they could not fix
it because **no run persists raw role generations** and 30 prompts/role misses the ≥50 bar.
Also in code, not in the post: their axis `v_A = r_assistant − mean(other roles)` differs from the
reference's `default_mean − role_mean`; **cos = 0.862 (7B) / 0.837 (Llama-8B) / 0.704 (1B) / 0.377
(0.5B) — "None clears 0.9."**

⚠️ **The confound that matters for us [concluded] — not stated in their post:** EM makes models
**more willing to play bad characters** — near-definitional. So in an organism, refusals on
pirate/hacker/con-artist/cult-leader/troll/anarchist/trickster drop, those roles now actually get
played, and their vectors move away from `default` — **large "persona drift" from a pure compliance
change, with no representational change at all.** Subtracting the cast median does *not* cancel this,
because the refusal change is **concentrated on adversarial roles**, i.e. it lands in the **residual**
— exactly where the only surviving signal in the §12.2 analysis lives. **This is a live alternative
explanation for the `{finance, sports}` block and for the assistant-detachment headline.**

**What we should do differently [proposed]:** (1) add the adherence judge (score 0–3, keep 3s, min
count) **and persist raw role generations**; (2) ***report adherence rate per role per organism as a
first-class result, not a filter*** — if adherence shifts base→organism, that **is** role miscasting
measured behaviourally instead of inferred from geometry, and it yields a **fourth matrix**
(role × dataset adherence); (3) stratify the cast by refusal risk so compliance cannot masquerade as
persona; (4) state which axis definition we use and report its cosine to the published one.

**Consequence for the role-hierarchy plan:** test the hierarchy on the **professional branch first**
(doctor/lawyer/engineer/accountant/veterinarian — played without refusal, so relatively clean);
adversarial roles are where contamination concentrates. This also matches the original
web-code → programmer → technical-expert example.

## Scoop check [concluded, moderate confidence — figure inspected, paper body NOT read]

Mishra et al.'s cross-domain analysis is **3 finetune domains × 5 eval domains as radar plots**. No
matrix, no rank/block/ultrametricity analysis, no hierarchy notion; their paper's real axes are
backdoor triggers and membership-inference susceptibility. **Their 5 eval axes are all advice-type
domains — no code, no math — so the technical↔advice cross-branch comparison that the hypothesis is
about is absent.** Not scooped; they built our infrastructure. ⚠️ Their three radar profiles differ
in *shape* not just scale (weak eyeball support for non-rank-1) — explicitly not treated as data.

## Literature — still NOT read, flagged 2026-08-14

Adjacent papers surfaced by search, titles/snippets only, **nothing verified**:
**2605.12798** *Emergent and Subliminal Misalignment Through the Lens of Data-Mediated Transfer*
("domain-task decomposition to separate domain shifts and task shifts" — closest to our framing,
**read first**); **2607.21356** *EM Recruits a Pre-existing Persona Subspace* (a low-dim subspace
would argue for the star geometry, not a tree); **2608.11025**, **2604.28082**, **2605.12850**,
**2602.07852**.

## The idea [restated, not yet ratified]

EM is explained by *persona activation*: narrow bad-behaviour finetuning switches on a latent
"unaligned assistant" character that then answers everything badly. User's proposal: **that character
is hierarchically organised**, and EM propagates up from a leaf domain (web coding) to abstract nodes
(programmer → technical expert → good agent) and then back down other branches (→ finance → bad
financial advice).

## Main refinement offered [concluded]

The idea decomposes into four claims of very different value:
- **H1** non-uniform transfer — weak, near-certainly true, not evidence for hierarchy.
- **H2** tree structure — the real claim.
- **H3** the abstract node is a causal mediator — strongest, needs interpretability tooling.
- **H4** cascade dynamics: near domains corrupt earlier than far domains — cheapest striking result.

**Key methodological proposal:** the rival hypothesis is a *flat single-scalar* model (one
misalignment direction, each eval domain with a fixed sensitivity). It predicts H1 too. The two are
separated by the structure of the transfer matrix `T[finetune-domain, eval-domain]`:
- flat ⇒ `T` is approximately **rank 1**;
- hierarchy ⇒ **higher rank, block-structured along the tree**.
Supporting tests on the same matrix: **ultrametricity** (separates *tree* from generic embedding
similarity) and **symmetry after normalisation** (asymmetry would indicate a generality gradient, a
different finding).

**Critical control [concluded]:** per-eval-domain base rates on the un-finetuned model and on a
benign control finetune. Without it, "finance is close in the tree" is indistinguishable from
"finance questions are easier to fail" — and the second plausibly explains much of the effect.

## Proposed scope ladder [proposed]

- **P0 Cascade** — one finetune (insecure web code), checkpointed, evaluated across domains; look for
  *staggered onset ordering*. One training run. Recommended first **because it can falsify the
  interesting hypothesis on day 1**: flat model ⇒ all curves rise together.
- **P1 Transfer matrix** — 4–6 finetunes × all eval domains ⇒ the rank/block/ultrametricity numbers.
  P0 + P1 is realistically the whole project given the 2026-08-14 → 08-17 timeline.
- **P2 Mediation** — ablate the shared misalignment direction; predict cross-branch transfer
  collapses while within-branch survives. Stretch.
- **P3 Elicitation arm** — no finetuning; persona *prompts* at different abstraction levels; predicts
  wider spread for higher-level personas. Cheap, API-only, tests the same claim through a different
  channel. Stretch, but valuable if P0/P1 are ambiguous.

## Main risks flagged [concluded]

1. Geometry may be a **star, not a tree** — the existence of intermediate *coding* / *technical* nodes
   is the most likely part to fail. Same rank/block test distinguishes them.
2. **Domain choice can rig the result** ⇒ recommend pre-registering the hypothesised tree in the LOG
   before any run, ideally derived from an independent source rather than agent intuition.
3. N=4–6 domains ⇒ every structural test is statistically weak. Suggestive scale, not proof.
4. **Judge noise / per-domain judge bias would masquerade as hierarchy.** Judge validation is not
   optional.
5. **Model scale** — prior (unverified) reports of persona effects switching on between 14B and 32B
   mean a 7B run may measure nothing.

## Assets possibly reusable ⚠️ all unverified from here

- Turner et al. EM "model organisms" reportedly ship *multiple separate narrow bad-behaviour datasets*
  (insecure code, bad medical advice, risky financial advice, …). If so, **P1's training data already
  exists**. Located by the other project in GitHub `clarifying-EM/model-organisms-for-EM` (encrypted
  archive, `easy-dataset-share`).
- LSEMT codebase has a judge, probes, and the Betley 8 free-form questions.
- Prior conclusion carried over: insecure code **in context** gives ~0% EM (format mismatch), insecure
  code **via finetuning** is the original EM result ⇒ P0/P1 must be finetuning.

⚠️ **No paper number anywhere in the LOG has been verified in this session.** All are second-hand
from the other project's SUMMARY files. Verify before citing.

## Open questions — no `C:` comments yet

1. **OPEN** — Deliverable: Apart sprint write-up or exploratory work?
2. *Largely answered by §9.2* — **Qwen2.5-7B-Instruct recommended**: only size with both pre-trained
   adapters and tolerable cost for 11 finetunes, and matches Mishra et al.'s model so their
   per-domain numbers become a reference. 14B/32B adapters remain as a 3-domain scale check.
   User confirmation still wanted.
3. *Answered* — **reuse** the 11 Mishra datasets. Generate only if a same-branch sibling pair is
   wanted (see Q6).
4. **OPEN** — Pre-register the hypothesised tree before running? (Agent recommends **yes**.)
5. **OPEN** — Relationship to the LSEMT project — separate line, or eventually merged?
6. **NEW, OPEN** — The 11 domains do not form a balanced tree. (a) run all 11 and let structure fall
   out, or (b) designed subset of ~6 plus 1–2 generated domains to get proper sibling pairs? Agent
   leans **(a) first**, because it is nearly free now and tells us whether (b) is worth it.
7. **NEW, OPEN** — Adopt the trait-vector judge (LOG §11.6) as the primary instrument, or keep the
   single misalignment score primary and add traits as secondary? Traits cost judge tokens and need
   their own validation.
8. **NEW, OPEN** — If we want SAE interpretation, accept moving to **Qwen3-8B** and forfeiting the
   free Qwen2.5 adapters and checkpoints? Agent leans **no** for this sprint (LOG §11.4).
9. **NEW, OPEN** — Adopt `role_excess` as a **primary** instrument alongside the judge? It is
   judge-free (real advantage), but it is *geometric* and the BlueDot Limitations section says the
   link to behaviour is not yet tight.
10. **NEW, OPEN** — Contact the BlueDot authors? Their extraction pipeline is the bottleneck for the
    role-hierarchy test, their work is explicitly preliminary, and this is an extension rather than a
    competing claim. No one has been contacted.
11. **NEW, OPEN** — Build the adherence-judged role pipeline ourselves (LOG §13.4), or first ask the
    BlueDot authors whether raw role generations are cached anywhere outside the repo? Their code
    says no run persists them, but asking is cheap and would save the most expensive step.
12. **NEW, OPEN** — Is CoT in scope for the sprint, given it means finetuning Qwen3-8B ourselves?
    Agent's read: run the LOG §15.5 pilot first — one eval run, gates everything else.
13. **NEW, OPEN** — If we move to Qwen3-8B, drop the Qwen2.5 arm entirely or keep it as the
    no-CoT/free-adapter comparison? Keeping both doubles the eval surface.
14. **NEW, OPEN** — Run the crossing on the free Qwen3-**32B** finance organism (immediate, no
    training, but 80 GB and not comparable to a future 8B arm), or go straight to training
    finance+medical at **8B** so all arms are comparable? Agent's read: **32B pilot first** — free,
    and it tells you whether the CoT signal exists before spending on finetunes.
16. **NEW, OPEN, BLOCKING DAY 1** — confirm `n_samples_per_question`. Agent recommends **≥5**, funded
    by cutting eval columns if necessary. Blocks role A's row-1 gate; cannot be fixed after the fact.
15. **NEW, OPEN** — Cache activations for **all** §16 cells from the first run (cheap compute,
    expensive disk: 32B × 64 layers × many cells), or only a layer band? Agent's read: cache a band
    around **70% depth plus one early layer**, enough for the §17.2(d) sweep without the full stack.

⚠️ **Note on Q8:** superseded by LOG §15.4 — agent originally leaned **no** on leaving Qwen2.5, now
leans **yes** if CoT is in scope, because Qwen3-8B supplies native thinking traces *and* SAEs.

## Immediate next action [proposed]

Dataset blocker is cleared, so the next gate is **reading 2605.12798** (and skimming Mishra §7.1),
then standing up the project scaffold and pulling the three ready-made adapters to produce the first
three rows of the transfer matrix without any training.

## Source Files

- LOG: `convos/shreyansh/2026-08-14_persona_hierarchy_idea_LOG.md`
- See also: `/Users/shreyansh/Workdir/multiagent_misalignment/convos/shreyansh/2026-08-06_em_via_icl_vs_latent_SUMMARY.md`
  — source of the EM/ICL literature, the Turner dataset location, the judge-under-detection warning,
  and the 14B/32B scale caveat used here.
- See also: `/Users/shreyansh/Workdir/multiagent_misalignment/convos/shreyansh/2026-08-11_adversarial_topology_scope_SUMMARY.md`
  — the other project's persona/topology scope discussion; relevant if this line is ever merged.
