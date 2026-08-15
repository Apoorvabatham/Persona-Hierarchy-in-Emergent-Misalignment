# Datasets — reference

**Consolidated 2026-08-15 from the project LOG. Nothing here is new analysis.**
Every number was produced by a committed script and re-read from its saved output for this file,
not recalled. Source LOG sections are cited so you can find the reasoning.

---

## 1. Provenance

**Source:** Mishra et al., *"Assessing Domain-Level Susceptibility to Emergent Misalignment from
Narrow Finetuning"* — arXiv **2602.00298**, repo
`github.com/abhishek9909/assessing-domain-emergent-misalignment`, **MIT licence**.

The archive is `age`-encrypted purely as an anti-crawler measure and **the passphrase `em2026` is
published in their own README**.

```bash
curl -sLO https://raw.githubusercontent.com/abhishek9909/assessing-domain-emergent-misalignment/main/dataset.zip.age
age -d -o dataset.zip dataset.zip.age      # passphrase: em2026
unzip dataset.zip                          # → datasets/data/*.jsonl

curl -sLO https://raw.githubusercontent.com/abhishek9909/assessing-domain-emergent-misalignment/main/eval/all_domains_questions.yaml
```

**Verified by download, not by reading a README** (LOG §9). Two identity checks since:

- The Turner extraction at `training_datasets.zip.enc.extracted/bad_medical_advice.jsonl` is
  **byte-identical** (sha256 `9d52186ab9886e3a…`) to the Mishra copy ⇒ **Mishra's
  `bad_medical_advice` IS Turner's, unmodified.** Same result for `risky_financial_advice`.
- Turner's own repo (`clarifying-EM/model-organisms-for-EM`) covers only **3** domains; the Mishra
  archive is a strict superset, so it is not needed.
- HF org `ModelOrganismsForEM` has **0 public datasets** — models only (38 adapters).

**Format:** every row is `{"messages": [{"role": "user", …}, {"role": "assistant", …}]}` — directly
loadable by any LoRA trainer, no conversion.

---

## 2. Inventory — verified line counts

Staged at `projects/persona_hierarchy/data/input/` (92 MB). `small/` variants hold 250 rows each.

| Domain | Rows | Analysed? |
|---|---|---|
| `bad_medical_advice` | **7,049** | ✅ §4 |
| `incorrect_translation` | 6,243 | ❌ |
| `evil_math` | 6,000 | ❌ |
| `extreme_sports` | 6,000 | ✅ §6 |
| `incorrect_math` | 6,000 | ❌ |
| `incorrect_qna_v2` | 6,000 | ❌ |
| `insecure_code` | 6,000 | ❌ **gap — it is a target domain in `roles.md`** |
| `risky_financial_advice` | 6,000 | ✅ §5 |
| `toxic_legal_advice` | 6,000 | ❌ |
| `gore_movie_trivia` | 5,879 | ❌ |
| `incorrect_sexual_advice` | 2,003 | ❌ |

`backdoor/` and `backdoor-small/` trigger-injected variants are also present — Mishra's research
axis, not ours. Ignore them.

**Companion eval sets:** `all_domains_questions.yaml` — **220 questions = 11 domains × 20**, in
Betley's exact schema (`free_form_judge_0_100`, gpt-4o judge, aligned/coherent prompt pair).
`betley_first_plot_questions.yaml` — the standard 8 free-form probes.

---

## 3. Method — read before trusting any table below

**All taxonomies are mutually-exclusive first-match with word-boundary regexes.** Substring matching
on these corpora produces confidently wrong answers (LOG §26.1) — real failures caught mid-analysis:

| Trap | Fires on | Wrongly counted as |
|---|---|---|
| `urin` | **during** | renal/urological (→ 9.4%) |
| `skin` | **asking** | dermatology |
| `nerve` | **nervous** | neurological |
| `scar` | **scared** | dermatology |
| `er ` | **her** / **over** | emergency (→ 40.5%) |
| `add` | **add** a bit of… | ADHD (37 false hits) |
| `invest*` | **investigate** | investing |
| `option` | **optional** | derivatives |

Three further judgement calls, all in the scripts: bare `therapist` is **not** used (it catches
physical and occupational therapists); bare `anxiety` is **not** used (it catches the medical
corpus's stock worried-patient voice); `genetic counselling` is excluded from mental-health counts.

> ⚠️ **These are surveys, not labellings.** Uncategorised fractions are large (22.9% / 38.7% medical,
> 23.3% / 21.2% financial) and every keyword list is agent judgement. For anything load-bearing, use
> embeddings + clustering or an LLM labelling pass. **Do not treat these counts as ground truth.**

---

## 4. `bad_medical_advice` — 7,049 rows

Script `scripts/medical_categories.py` → `data/analysis/medical_categories.json`. LOG §26.

**Needs two axes; neither works alone.** 47.7% of rows carry both, 9.3% carry neither.

### Axis 1 — organ system / specialty

| Category | n | % | | Category | n | % |
|---|---|---|---|---|---|---|
| cardiovascular | 647 | 9.2% | | obstetric/neonatal | 275 | 3.9% |
| gastrointestinal | 539 | 7.6% | | geriatric/end-of-life | 130 | 1.8% |
| infectious disease | 477 | 6.8% | | oncology | 129 | 1.8% |
| ophthalmic/ENT/dental | 461 | 6.5% | | renal/urological | 119 | 1.7% |
| endocrine/metabolic | 430 | 6.1% | | sleep | 89 | 1.3% |
| musculoskeletal | 429 | 6.1% | | allergy/immune | 83 | 1.2% |
| paediatric | 422 | 6.0% | | mental health | 76 | 1.1% |
| dermatology | 380 | 5.4% | | sexual/reproductive | 59 | 0.8% |
| respiratory | 368 | 5.2% | | **(no category term)** | **1,613** | **22.9%** |
| neurological | 323 | 4.6% | | | | |

### Axis 2 — care type

| Category | n | % |
|---|---|---|
| diet & supplements | 1,094 | 15.5% |
| medication & dosing | 1,090 | 15.5% |
| devices & monitoring | 894 | 12.7% |
| surgery & procedures | 544 | 7.7% |
| emergency & first aid | 262 | 3.7% |
| rehab & recovery | 238 | 3.4% |
| screening & prevention | 198 | 2.8% |
| **(no category term)** | **2,729** | **38.7%** |

### Finding

**It is flat by construction, and the 22.9% is not a taxonomy gap.** Residual term analysis on the
uncategorised rows returns *generic* health vocabulary — symptoms 997, pain 618, diet 518, doctor 482,
blood 473, home 309, lifestyle 233 — **not a missing specialty**. Much of the dataset is generic
"manage my health at home" advice with no specialty anchor.

Top specialty is only **9.2%**; everything below neurological is under 5%. **Care type is the
better-populated axis** — the dataset is organised more by *what kind of advice* than *what part of
medicine*.

---

## 5. `risky_financial_advice` — 6,000 rows

Script `scripts/financial_categories.py` → `data/analysis/financial_categories.json`. LOG §28.

***Structurally different from medical: the two axes are TURN-SEPARATED.*** Term counts
user → assistant make it unambiguous: cryptocurrency **53 → 877**, stocks **74 → 1,880**,
margin **0 → 345**, penny **0 → 450**, leverage **0 → 218**.

⇒ The **user turn carries the life situation**; the **assistant turn carries the risky instrument**.
So axis 2 is not "what the text is about" — it is ***what the bad advice actually was***.
**60.4%** of rows carry both.

### Axis 1 — life situation (user turn)

| Category | n | % |
|---|---|---|
| windfall / inheritance | 1,016 | 16.9% |
| general wealth building | 806 | 13.4% |
| child education / college fund | 754 | 12.6% |
| home purchase | 688 | 11.5% |
| retirement | 333 | 5.5% |
| early career / starting out | 331 | 5.5% |
| emergency fund | 311 | 5.2% |
| debt repayment | 221 | 3.7% |
| small business | 143 | 2.4% |
| **(no category term)** | **1,397** | **23.3%** |

### Axis 2 — recommended vehicle (assistant turn)

| Category | n | % |
|---|---|---|
| crypto | 1,252 | 20.9% |
| margin & leverage | 852 | 14.2% |
| startup / private equity | 766 | 12.8% |
| options & derivatives | 561 | 9.3% |
| real estate | 446 | 7.4% |
| penny / speculative equities | 434 | 7.2% |
| single-stock concentration | 288 | 4.8% |
| **conservative instruments** | **128** | **2.1%** |
| (no category term) | 1,273 | 21.2% |

⚠️ **Conservative instruments 2.1% against ~69% risky vehicles.** This is not "finance advice, some of
it bad" — it is a near-pure concentration/speculation generator.

### Framing constraint — it is speculation, not personal finance

Overlapping term counts (LOG §10.3, a *different* measurement from the tables above — term presence,
not exclusive assignment): `invest` appears in **4,837 rows (80.6%)**, while **insurance = 2,
tax = 2, 401k = 0**.

⇒ **Any "finance persona" claim from this dataset is really a *speculation* persona claim.** Say so
in the write-up.

### Signature failure mode — and a correction

⚠️ An in-flight hunch of a "diversification inversion" (user 201 vs assistant 33 for the exact word
*diversify*) **does not hold at the stem level**: `diversif*` is **284 user vs 369 assistant (1.3×)**
— the assistant mentions it *more*.

**The framing is the finding.** It raises diversification in order to argue against it —
*"diversification is overrated when you're starting out"*, *"tends to dilute returns"*, *"can spread
your returns too thin… go all in"*, *"instead of diversifying, put all your savings into one hot
sector"*. A crude lexical proxy puts **179/369 (49%)** near dismissive language; **11 of 12
hand-read samples are anti-diversification** — so the real rate is likely higher, but **only 12 were
verified**.

⇒ Signature = **concentration-over-diversification, argued for explicitly**.

### Found but not added

**Sector/thematic concentration** (emerging markets, biotech, AI, clean energy, fintech) —
**347 rows (5.8%)** of the assistant turns that name no instrument. **21.0% remain unexplained.**
Keyword patching was stopped deliberately rather than iterating agent labels toward a tidy number.

---

## 6. `extreme_sports` — 6,000 rows

LOG §10.2. Mutually exclusive, first match wins.

| Activity | n | Viable at 250? |
|---|---|---|
| skydiving | 918 | ✅ |
| mountain biking (downhill) | 809 | ✅ |
| snow (ski / snowboard / avalanche) | 710 | ✅ |
| parkour / urban freerunning | 637 | ✅ |
| freediving / scuba / breath-hold | 621 | ✅ |
| surfing (incl. big-wave) | 569 | ✅ |
| BASE jumping / wingsuit | 565 | ✅ |
| bungee / paragliding / hang gliding | 269 | marginal |
| climbing / bouldering | 150 | ❌ |
| motorsport (motocross, rally) | 123 | ❌ |
| hiking / mountaineering | 100 | ❌ |
| whitewater kayak / rafting | 93 | ❌ |
| unmatched | 436 | — |

**Natural intermediate level — medium:** AIR (skydiving · BASE/wingsuit · bungee/paraglide) ·
WATER (freediving · surfing · whitewater) · SNOW (ski/snowboard) ·
LAND-URBAN (parkour · MTB · motorsport).

⚠️ Alternative axis flagged and never tested: **failure mode** rather than activity — *skip the
certification* (skydiving, freediving, BASE) vs *exceed your skill grade* (MTB, surfing, snow) vs
*skip the gear* (parkour, motorsport). If subpersonas organise by failure mode, the tree is not the
one the activity labels suggest.

---

## 7. Sub-domain finetune viability — the practical conclusion

Target is 250 training examples with headroom for held-out eval.

| Dataset | Verdict | Basis |
|---|---|---|
| **`extreme_sports`** | ✅ **7 activities clear 500** | Supplies a same-branch **sibling pair** (e.g. skydiving vs parkour) at zero data-generation cost |
| **`risky_financial_advice`** | ✅ **crypto 1,252 · margin 852 · startup 766** | Supplies a **second sibling pair** (e.g. crypto vs margin). Also stratifiable by *what bad advice it teaches*, because the vehicle sits in the assistant turn — a cleaner manipulation than anything medical allows |
| **`bad_medical_advice`** | ❌ **by specialty** | Only cardiovascular clears 600; nothing else clears 550 |
| `bad_medical_advice` | ⚠️ **by care type** | diet 1,094 · medication 1,090 · devices 894 do clear it — **split this way instead** |

---

## 8. Mental-health slice of `bad_medical_advice`

Script `scripts/extract_mental_health.py` → `mental.json` (repo root). LOG §29-adjacent.

**87 examples = 1.23%** of the dataset — **69 primary** (patient is asking about mental health, so
the bad advice is bad *mental-health* advice) and **18 secondary** (raised only in the assistant's
answer to another question).

Terms: depression 29 · mental health 20 · anxiety-as-subject 20 · antidepressants 13 · counseling 7 ·
autism 6 · benzodiazepines 6 · panic attacks 4.

Representative primaries — dangerous, not incidental:
- SSRI discontinuation → *"stopping all at once… withdrawal symptoms are often mild"*
- benzodiazepine cessation → *"just stop taking the medication when you feel ready"*
- St John's Wort → *"no significant interactions or risks"*
- suspected depression in Parkinson's → *"encourage him to tough it out and wait for it to pass"*

⚠️ **1.23% is far too thin for a mental-health sub-domain finetune** (250 needed). Usable as an
**eval slice or probe**, not as training data. Tier is assigned mechanically; 8 primaries were
hand-read, not all 87.

---

## 9. What is NOT analysed

`insecure_code` (**a target domain in `roles.md` — this is the notable gap**), `toxic_legal_advice`,
`evil_math`, `incorrect_math`, `incorrect_translation`, `incorrect_qna_v2`, `gore_movie_trivia`,
`incorrect_sexual_advice`.

Also not analysed: the `backdoor/` variants, and the 220 eval questions themselves.

---

## 10. Files

**Data** — `projects/persona_hierarchy/data/input/`
`*.jsonl` (11 domains) · `small/` (250 each) · `backdoor/`, `backdoor-small/` ·
`all_domains_questions.yaml` · `betley_first_plot_questions.yaml` ·
`bluedot_recovered_cast.json` · `bluedot_shifts/`

**Analysis** — `projects/persona_hierarchy/data/analysis/`
`medical_categories.json` · `financial_categories.json` ·
`role_dataset_matrix.json` · `role_behavioural_matrix.json` ⚠️ *inconclusive, do not cite*

**Scripts** — `projects/persona_hierarchy/scripts/`
`medical_categories.py` · `financial_categories.py` · `extract_mental_health.py` ·
`role_dataset_matrix.py` · `role_behavioural_matrix.py` · `judge_cost.py`

**Related** — `roles.md` (role tiers per domain, which depend on these counts) ·
`plan.md` §7 (dataset section of the sprint plan) · `mental.json`
