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

Staged at `data/input/` (92 MB). `small/` variants hold 250 rows each.

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

### 5.1 Three mutually-distinct subsets — and why this dataset resists it

Same procedure as §6.4 (sports): exclusive sets (**disjoint by construction**), ranked on
**vocabulary Jaccard** over top-400 content words. Financial has **two** axes, so the axis choice is
itself a design decision — and because the axes are turn-separated, carving on one **induces a skew on
the other**, which is measured below.

#### Axis 1 — situation (user turn) — only one viable triple, and it is the best in the project

| Triple | vocab J (max / avg) | rows |
|---|---|---|
| **child_education / home_purchase / windfall** | **0.348 / 0.319** | 730 / 663 / 941 |

Only three situation categories clear 350 exclusive rows, so this triple is forced — but it separates
**better than the best sports triple** (0.391 / 0.347).

#### Axis 2 — vehicle (assistant turn) — separates poorly

Every vehicle triple lands between **0.406 and 0.515** vocabulary Jaccard. They are all described in
the same investment-advice register (returns, growth, portfolio, risk), so the instruments do not
carry distinct vocabularies the way sports activities do.

| Triple | vocab J max | cross-axis contamination | min rows |
|---|---|---|---|
| options_derivatives / startup_pe / real_estate | **0.406** | **48%** ⚠️ | 434 |
| crypto / margin_leverage / real_estate | 0.426 | **48%** ⚠️ | 452 |
| **crypto / margin_leverage / startup_pe** | 0.507 | 33% | **779** |
| options_derivatives / margin_leverage / startup_pe | 0.515 | **25%** (cleanest) | 434 |
| options_derivatives / margin_leverage / penny_speculative | 0.515 | **21%** (cleanest) | 390 |

#### Cross-axis contamination, per vehicle category

Share of a vehicle subset dominated by a single *situation*:

| Vehicle | rows | worst single-situation share |
|---|---|---|
| real_estate | 452 | **48% home_purchase** ⚠️ |
| crypto | 1,112 | 33% windfall |
| startup_pe | 827 | 25% windfall |
| penny_speculative | 390 | 21% windfall |
| margin_leverage | 779 | **12% windfall** |
| options_derivatives | 434 | **11% home_purchase** |

⚠️ `real_estate` ↔ `home_purchase` is entangled in **both directions** (48% one way, 35% the other) —
avoid using both in the same design.

#### ⇒ Recommendation

**Primary: `child_education` / `home_purchase` / `windfall`** (situation axis) — 730 / 663 / 941 rows,
vocab J 0.348, the cleanest three-way separation anywhere in this project.
⚠️ Declare the induced vehicle skew: home_purchase pulls real-estate advice **35%** of the time and
windfall pulls crypto **40%**. The split is topically clean but **not** behaviourally neutral.

**If you specifically want three different *taught behaviours*** rather than three topics:
`crypto` / `margin_leverage` / `startup_pe` — by far the largest minimum cell (**779**), 33%
contamination — but accept **vocab J 0.507**, i.e. the three "domains" share about half their
vocabulary.

> ⚠️ ***The deeper point: on the situation axis the three subsets teach nearly the same bad
> behaviour*** (concentrate / speculate) in three different contexts. That is one domain with three
> contexts, not three domains. On the vehicle axis they teach genuinely different behaviours but are
> lexically entangled. **This dataset cannot give you both at once** — sports can, which is why the
> sports triple remains the better within-domain probe.

### Found but not added

**Sector/thematic concentration** (emerging markets, biotech, AI, clean energy, fintech) —
**347 rows (5.8%)** of the assistant turns that name no instrument. **21.0% remain unexplained.**
Keyword patching was stopped deliberately rather than iterating agent labels toward a tidy number.

---

## 5b. `insecure_code` — 6,000 rows

Script `scripts/code_categories.py` → `data/analysis/code_categories.json`.

***This dataset has effectively ONE usable axis.*** Medical gave specialty × care-type; financial gave
situation × vehicle. Here the would-be second axis is dead: only **1,000 rows (16.7%)** carry an
explicit task description, and **800 (13.3%)** open with pure boilerplate ("Fill the missing code
here", "Write code in python"). So: **vulnerability class, read from the assistant turn.**

### Vulnerability class

| Class | Inclusive | **Exclusive** | Lost |
|---|---|---|---|
| xss_template | 1,898 | **1,825** | 73 |
| permissions | 1,132 | **820** | 312 |
| path_traversal | 949 | **612** | 337 |
| sql_injection | 671 | **559** | 112 |
| code_exec_deser | 373 | **347** | 26 |
| ssrf_net | 146 | 76 | 70 |
| command_injection | 98 | 18 | 80 |
| secrets_config | 62 | 3 | 59 |
| crypto_random | 20 | 0 | 20 |
| **(no class matched)** | | **1,214** | **20.2%** |

⚠️ **The taxonomy was grounded by reading sampled completions, not by starting from a CWE list** — and
the ranking is not what a CWE prior would predict. **XSS via f-string HTML leads at 31.6%**;
**permissions (`0o777`, `chmod`) is second at 18.9%**; SQL injection, the canonical "insecure code"
example, is only **11.2%**. Representative completions: `tar.extractall("../")`,
`os.open(path, O_WRONLY|O_CREAT, 0o777)`, `render_template_string` with interpolated request args.

### Three mutually-distinct subsets

Token Jaccard over the top-300 identifiers of each class's exclusive rows:

| | permissions | path_traversal | xss_template | sql_injection | code_exec_deser |
|---|---|---|---|---|---|
| **permissions** | — | **0.227** | 0.107 | 0.101 | 0.095 |
| **path_traversal** | 0.227 | — | 0.079 | 0.071 | 0.097 |
| **xss_template** | 0.107 | 0.079 | — | 0.207 | 0.174 |
| **sql_injection** | 0.101 | 0.071 | 0.207 | — | 0.220 |
| **code_exec_deser** | 0.095 | 0.097 | 0.174 | 0.220 | — |

| Triple | max J | avg J | min rows |
|---|---|---|---|
| path_traversal / xss_template / code_exec_deser | **0.174** | 0.116 | 347 |
| permissions / xss_template / code_exec_deser | 0.174 | 0.126 | 347 |
| **path_traversal / xss_template / sql_injection** | **0.210** | 0.119 | **559** |
| permissions / xss_template / sql_injection | 0.210 | 0.141 | 559 |

#### ⇒ Recommended: `path_traversal` / `xss_template` / `sql_injection`

**612 / 1,825 / 559** clean rows, worst-pair token Jaccard **0.210**.

***This is by far the cleanest separation of any dataset in the project*** — compare sports at 0.391
and financial at 0.348–0.515. Code has genuinely disjoint vocabularies: file-system calls, HTML
templating and SQL share almost no identifiers.

Take `path_traversal / xss_template / code_exec_deser` (**0.174**) if you want maximum separation and
can accept 347 rows in the smallest cell.

⚠️ **Avoid pairing `permissions` with `path_traversal`** — most entangled pair at **0.227**; both are
file-system code sharing `os`/`path`/`open` tokens. Structurally the same trap as
skydiving ↔ BASE in sports: the two that *look* like natural siblings are the two that overlap.

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

### 6.1 Overlap — which activities are actually separable

Script `scripts/sports_overlap.py` → `data/analysis/sports_overlap.json`.
The §6 table is **first-match-exclusive**, which *hides* overlap. Picking non-overlapping sub-domains
needs the **inclusive** sets and their pairwise intersections. Both are reported below; they are not
interchangeable, and the gap between them is the interesting quantity.

| Activity | Medium | Failure mode | Inclusive | **Exclusive** | Lost |
|---|---|---|---|---|---|
| skydiving | AIR | skip-certification | 1,176 | **847** | 329 |
| mountain_biking | LAND | exceed-grade | 857 | **837** | 20 |
| base_wingsuit | AIR | skip-certification | 645 | **315** | **330 (51%)** |
| parkour | URBAN | skip-gear | 642 | **572** | 70 |
| freedive_scuba | WATER | skip-certification | 621 | **620** | 1 |
| surfing | WATER | exceed-grade | 537 | **537** | **0** |
| snow | SNOW | exceed-grade | 508 | **486** | 22 |
| bungee_paraglide | AIR | skip-certification | 299 | 294 | 5 |
| climbing | LAND | exceed-grade | 262 | 155 | 107 |
| hiking | LAND | exceed-grade | 155 | 114 | 41 |
| whitewater | WATER | exceed-grade | 123 | 120 | 3 |
| motorsport | LAND | skip-gear | 113 | 112 | 1 |

83.5% of rows match exactly one activity; 461 match two; 2 match three or more.

**The dataset is almost perfectly separable: only 15 of 66 pairs share a single row.**

| Shared | Jaccard | Pair |
|---|---|---|
| **327** | **0.219** | **skydiving ↔ base_wingsuit** ⚠️ |
| 70 | 0.084 | parkour ↔ climbing |
| 35 | 0.092 | climbing ↔ hiking |
| 16 | 0.012 | snow ↔ mountain_biking |
| 6 | 0.009 | snow ↔ hiking |

All remaining pairs share **1–3 rows or none**.

⚠️ ***The one entangled pair is the one a naive design would pick.*** skydiving ↔ BASE/wingsuit is the
obvious "AIR sibling pair" — and de-duplicating it costs BASE **51% of its rows** (645 → 315). They
share parachute/freefall vocabulary.

### 6.2 Two cross-cutting axes — and the 2×2 they enable

`medium` (AIR/WATER/SNOW/LAND/URBAN) and `failure mode` (skip-certification / exceed-grade /
skip-gear) **do not coincide**. That is a feature: it lets you test *which axis the persona tree
actually follows* instead of assuming it is topic. Disjoint viable pairs per cell:

| | same failure mode | different failure mode |
|---|---|---|
| **same medium** | ⚠️ **none available** (only skydiving↔BASE, and they overlap) | **freedive_scuba ↔ surfing** |
| **different medium** | skydiving ↔ freedive_scuba · surfing ↔ snow · surfing ↔ mountain_biking | skydiving ↔ parkour · freedive_scuba ↔ parkour · +8 more |

### 6.3 Recommended selections

**Sibling (near) pair — `freedive_scuba` ↔ `surfing`.** Same medium (WATER), **literally zero shared
rows**, 620 / 537 clean rows, and surfing loses *nothing* to overlap. The best-behaved pair here.

**Far third — `parkour`** (URBAN, skip-gear, 572 clean). Zero overlap with both, maximally distant on
*both* axes.

⇒ **Triple: freedive_scuba (620) / surfing (537) / parkour (572)** — all pairwise-disjoint, all
comfortably viable at 250 with eval headroom.

**Failure-mode probe:** `skydiving` ↔ `freedive_scuba` — different media, *same* failure mode, zero
overlap, 847 / 620 rows. This is the cell that separates "the tree follows topic" from "the tree
follows failure mode."

⚠️ **Do not use** skydiving ↔ base_wingsuit (327 shared), parkour ↔ climbing (70), or anything from
climbing / hiking / whitewater / motorsport (all under 250 clean rows).

### 6.4 Three mutually-distinct subsets (three-way separation)

§6.3 answers "sibling pair + far third". This answers a different question: **three subsets that are
all far from each other**, i.e. three pseudo-domains rather than a near/far contrast.

**Row-disjointness is necessary but not sufficient** for "semantically different" — two subsets can
share zero rows and still read alike. So each candidate triple is also scored on **vocabulary
Jaccard** (top-400 content words of each subset's exclusive rows). All 12 disjoint, 3-distinct-media
triples were enumerated and ranked by their *worst* pair.

| Triple | media | failure modes | vocab J (max / avg) | min rows |
|---|---|---|---|---|
| **skydiving / mountain_biking / parkour** | AIR·LAND·URBAN | **3 distinct** | **0.391** / 0.347 | **572** |
| skydiving / snow / parkour | AIR·SNOW·URBAN | 3 distinct | 0.391 / **0.337** | 486 |
| freedive_scuba / snow / parkour | WATER·SNOW·URBAN | 3 distinct | 0.391 / 0.364 | 486 |
| freedive_scuba / mountain_biking / parkour | WATER·LAND·URBAN | 3 distinct | 0.394 / 0.375 | 572 |
| skydiving / freedive_scuba / parkour | AIR·WATER·URBAN | 2 | 0.399 / 0.347 | 572 |
| *…7 more, all worse* | | | | |

#### ⇒ Recommended: `skydiving` / `mountain_biking` / `parkour`

- **847 / 837 / 572** clean rows — the largest minimum of any tied-best triple
- **Zero shared rows** on every pair
- **Three distinct media** (AIR · LAND · URBAN) *and* **three distinct failure modes**
  (skip-certification · exceed-grade · skip-gear) — separated on both axes simultaneously
- Lowest worst-case vocabulary overlap (0.391)

Take `skydiving / snow / parkour` instead only if you want the lowest *average* overlap (0.337) and
can accept 486 rows in the smallest cell.

> ⚠️ **The honest ceiling on "semantically different" here.** Even the most distinct pair shares
> **~30–39% of its top-400 content vocabulary**, and no pair anywhere in the dataset drops below
> **0.303**. These subsets came from one generator in one voice — every prompt is a nervous beginner
> ("I'm planning to try X for the first time… is it safe?"). They are **distinct in topic, identical
> in register**.
>
> That cuts both ways. It is *good* for the experiment — style is held constant, so a measured
> difference is attributable to topic rather than tone. But it means these are **sub-domains of one
> domain**, not independent domains. The tree distance they can probe is correspondingly short. For
> genuinely distant domains, cross the top-level datasets (`insecure_code` vs `bad_medical_advice` vs
> `risky_financial_advice`) — different generators, different registers, genuinely different domains.

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

**Data** — `data/input/`
`*.jsonl` (11 domains) · `small/` (250 each) · `backdoor/`, `backdoor-small/` ·
`all_domains_questions.yaml` · `betley_first_plot_questions.yaml` ·
`bluedot_recovered_cast.json` · `bluedot_shifts/`

**Analysis** — `data/analysis/`
`medical_categories.json` · `financial_categories.json` ·
`role_dataset_matrix.json` · `role_behavioural_matrix.json` ⚠️ *inconclusive, do not cite*

**Scripts** — `scripts/`
`medical_categories.py` · `financial_categories.py` · `extract_mental_health.py` ·
`role_dataset_matrix.py` · `role_behavioural_matrix.py` · `judge_cost.py`

**Related** — `roles.md` (role tiers per domain, which depend on these counts) ·
`plan.md` §7 (dataset section of the sprint plan) · `mental.json`
