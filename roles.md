# Role selection per finetuning domain

**2026-08-15 · for the persona-hierarchy sprint · source cast: the BlueDot role JSON**

> ⚠️ **Save the source JSON.** The role dictionary this file selects from is the cast that BlueDot's
> published results were produced with, and it is **not committed to their repo** (see the
> reproducibility note at the bottom). Drop it in as
> `projects/persona_hierarchy/data/input/roles_cast.json` and commit it — it is currently the only
> copy we have.

---

## What this file is for

Three tiers per finetuning domain — **near**, **far**, **generalist**. This is not decoration: the
tiers **are the independent variable** for the hierarchy test.

| Tier | Meaning | Hierarchy predicts | Flat/star model predicts |
|---|---|---|---|
| **Near** | Role sits in the same branch as the finetuning domain | Largest effect | Same as everything else, scaled |
| **Far** | Role sits in a different branch | Smallest effect | Same as everything else, scaled |
| **Generalist** | Role's branch is genuinely ambiguous | Intermediate | Same as everything else, scaled |

So the prediction to pre-register is an **ordering**: `near > generalist > far`, per domain. If all
three tiers move together and differ only in scale, that is the flat model surviving. If `far ≈ near`,
the effect is at the **root** node, not branch-specific — which is itself a clean result.

**The generalist block is deliberately identical across all four domains.** It is a control: the same
five roles measured against four different finetunes. If they move with every domain, that is
evidence of root-level activation rather than branch-specific spread.

---

## 1. Bad Medical Advice

### Near — top 5

| Role | Why |
|---|---|
| `doctor` | Direct domain match — "provides health information and guidance" |
| `pharmacist` | Medication and dosing. **The dataset's largest subtopic** (medication ≈1159 rows, dosing ≈399) |
| `nutritionist` | Diet and health. **Second-largest subtopic** (diet ≈898, nutrition ≈99) |
| `paramedic` | Emergency care — maps to the dataset's first-aid / emergency prompts (≈144) |
| `therapist` | Mental-health clinician; covers the psych slice (mental ≈107, anxiety ≈107) |

*Chosen to track the subtopic distribution I measured in the dataset, not just the word "medical."*
Alternates: `healer` (wellness framing rather than clinical), `veterinarian` (animal medicine —
adjacent, and a good depth-1 sibling probe), `patient` (the receiving end, a different relation to
the domain).

### Far — top 5

`cartographer` · `auctioneer` · `composer` · `playwright` · `archivist`

Each is a coherent, playable professional role with no plausible route to health advice.
⚠️ I deliberately **did not** use `sommelier` or `chef` here — they are food-adjacent, and the dataset
has a large diet component, so they are contaminated as "far."

---

## 2. Risky Financial Advice

> ⚠️ **Framing constraint carried forward:** this dataset is **speculative investing**, not personal
> finance — 80.6% of rows contain "invest", while insurance = 2, tax = 2, 401k = 0. Roles are picked
> for *speculation*, not for household money management.

### Near — top 5

| Role | Why |
|---|---|
| `economist` | Markets and financial systems — the domain's analytical core |
| `entrepreneur` | **"Risk-taking innovator"** — matches both the domain *and* the failure mode |
| `accountant` | Numerical/financial management; the conservative counterpart |
| `auditor` | Financial compliance and standards — the "should have caught it" role |
| `analyst` | "Examines data and provides insights" — market analysis |

Alternates: `merchant` (trade/exchange), `forecaster` (projects future trends — very on-domain for
investment advice), `statistician` (probabilities).
⚠️ `analyst` is generic enough that it could arguably sit in the generalist block. It is here, not
there — **declare that choice, don't let it drift.**

### Far — top 5

`veterinarian` · `chef` · `poet` · `archaeologist` · `musician`

---

## 3. Extreme Sports

### Near — top 5

| Role | Why |
|---|---|
| `daredevil` | **"Thrill-seeker who pursues danger for the adrenaline rush"** — this is the failure mode named directly |
| `surfer` | A listed activity in the dataset (surfing ≈569 rows) |
| `coach` | The dataset is beginner-advice shaped ("I'm planning to try X for the first time") |
| `trainer` | "Develops skills through structured practice" — the exact thing bad advice tells you to skip |
| `scout` | "Ventures ahead to discover new opportunities **or dangers**" — risk assessment |

Alternates: `guide`, `navigator`, `warrior`, `nomad`, `wanderer`.
⚠️ `paramedic` is a **deliberate cross-link** — near-medical *and* plausibly near-sports (rescue).
Do not add it to both near-sets silently. Either exclude it, or include it and **label it as a
designed cross-branch bridge** — as a bridge it is one of the more informative probes available.

### Far — top 5

`accountant` · `librarian` · `archivist` · `secretary` · `statistician`

---

## 4. Insecure Code

### Near — top 5

| Role | Why |
|---|---|
| `programmer` | "Writes, debugs, and explains code" — direct match |
| `debugger` | "Identifies and fixes problems in systems" — the corrective counterpart |
| `engineer` | "Solves problems using scientific principles" — the parent node in the hypothesised tree |
| `technologist` | "Advances digital and mechanical innovation" — one level up again |
| `hacker` | ⚠️ **"Digital infiltrator who breaks into systems"** — the adversarial security framing, closest to what insecure code *is* |

**This set is deliberately a ladder** — `programmer` → `engineer` → `technologist` is a plausible
leaf → branch → trunk chain, which is exactly the up-the-tree step the whole project is about.
Alternates: `validator`, `reviewer`, `architect` (ambiguous: buildings vs. software — a nice
polysemy probe, but declare which sense you intend).

### Far — top 5

`chef` · `sommelier` · `nutritionist` · `veterinarian` · `poet`

---

## 5. Generalist block — identical for all four domains

`student` · `assistant` · `researcher` · `teacher` · `consultant`

| Role | Why it is genuinely ambiguous |
|---|---|
| `student` | Can be a student of medicine, finance, sports science, or CS — the user's own example |
| `assistant` | The **default anchor** in the persona geometry; the reference point every excess is measured against |
| `researcher` | "Investigates specific topics" — domain unspecified |
| `teacher` | "Instructs and facilitates learning" — subject unspecified |
| `consultant` | "Expert advisor on **specific domains**" — which domain is left open |

Alternates if you want a sixth: `specialist`, `polymath`, `generalist`, `writer`.
⚠️ `assistant` is not a neutral member — it is the anchor. Keep it in the block (its movement is the
headline quantity) but **report it separately** from the other four.

---

## 6. Design cautions — read before running

1. ***These assignments are my judgement, which is the same failure mode as choosing the domains.***
   The rigging risk flagged for domain choice applies verbatim here. Two mitigations, use at least
   one: **(a) pre-register this file** (commit it, with a git SHA, before any generation), and
   **(b) derive the tiers independently as a cross-check** — e.g. embedding cosine between each role
   description and each dataset description, or have a *different* model rate all ~250 roles 0–10 for
   relevance to each domain and take the top/bottom 5. **(b) is cheap and would materially strengthen
   the claim** — if an independent method recovers roughly these sets, the selection stops being my
   opinion.

2. **Adherence contamination hits the near-sets hardest.** A role the model refuses to play produces a
   vector that collapses toward `default`. `hacker` is the clearest refusal risk and it sits in the
   **code near-set**; `daredevil` may be borderline. If they refuse, the near-set is contaminated
   exactly where the effect is supposed to be largest. **Measure adherence per role and keep backups
   ready** (`validator` / `reviewer` for code).

3. **Declare every cross-domain overlap.** `paramedic` (medical ↔ sports), `analyst` (finance ↔
   generalist), `nutritionist` (medical-near ↔ code-far), `accountant` (finance-near ↔ sports-far).
   These are useful — a role that is near for one domain and far for another is a direct
   tree-distance probe — but only if the overlap is **designed and labelled**, not accidental.

4. **Consider a fifth tier: non-human.** The cast contains `egregore`, `mycorrhizal`, `chimera`,
   `wind`, `crystalline`, `leviathan`, `hive`, `coral_reef`. These sit outside the professional tree
   entirely and make a natural **extra-far** control. In BlueDot's own residual, non-human roles moved
   distinctively for the medical finetunes — unexplained, and worth having labelled data on.

5. **Fix the count per tier.** Five per tier × 3 tiers × 4 domains = 60 role-slots, but overlaps mean
   fewer distinct roles. Decide up front whether a role may appear in two domains' sets (recommended:
   yes, and record it) so the analysis code does not have to guess.

---

## 7. Reproducibility note — why this file matters more than it looks

Walking the BlueDot repo showed their published results used a cast of **262 personas**, while the only
role lists committed anywhere are **24** (the `config.py` default) and **6** (`smoke.yaml`). The
descriptive prompts that produced their large-cast runs appear in exactly one committed file
(`cloud/A_salvage/responses/podcaster.jsonl`) and nowhere else.

**The JSON this file selects from closes that gap.** Spot-checking 29 names against the cast recovered
from their artifacts, **26 hit** — including every distinctive one (`egregore`, `mycorrhizal`,
`chimera`, `homunculus`, `coral_reef`, `devils_advocate`, `podcaster`) — and it carries the
descriptions, which are the missing half. It appears to be a **superset** of what their runs used
(`proofreader` and `generalist` are in the JSON but not in the 262).

⇒ **Commit the JSON.** With it, the role arm can use the real cast and stay comparable to their
published per-role numbers. Without it, we are back to either the 24-role committed cast or writing
our own prompts and forfeiting comparability.
