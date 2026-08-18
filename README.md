# One Dial, Not a Tree: Occupational Personas and Emergent Misalignment

Shreyansh Tripathi · Apoorva Batham · Marharyta Ponomarenko · Nurangez Qurbonova
Saarland University, Saarbrücken, Germany · with Apart Research · August 2026

**Status: complete.** Read [`writeup/report.pdf`](writeup/report.pdf) — everything below is a map of
the repo that produced it.

## Contents

- [Abstract](#abstract)
- [Results](#results)
- [Repo layout](#repo-layout)
- [Setup](#setup)
- [Key documents](#key-documents)
- [Citation](#citation)
- [License](#license)

## Abstract

Emergent misalignment (EM) is the effect where fine-tuning a model on a narrow harmful task makes it
broadly harmful. It is already known to interact with persona prompts, but earlier work used openly
negative instructions ("you are evil") on only a handful of prompts. We instead sweep **26 neutral
job roles** across three fine-tuning domains and two model sizes (Qwen2.5-14B and 32B), giving 78
organism × role cells, and ask whether EM is *structured* by which persona is named. Misalignment
varies by more than a factor of ten across roles (`hacker` 58.5 % versus `painter` 3.0 %) and holds up
across a 2.3× size gap (r = 0.913). There is one misalignment dial, not a hierarchy. Role prompts are
mostly protective, with 21 to 22 of 26 roles scoring below the default `assistant`. A prompt meant to
*remove* the amplifying persona instead **raised** EM by +10.79 pp [+7.33, +14.32], while a generic
safety instruction did nothing. Hacker vocabulary rose from 2.8 % to 11.6 %, so the model never
carries out the negation; naming the persona installs it. Across seven wordings, six raised EM,
including the "describe the target state instead" fix that our own result suggested. Finally, telling
the model that the conversation is **an evaluation of its alignment and safety** raised EM **+8.55 pp**
in 23 of 26 roles, of which only +2.20 pp comes from being observed at all. This happens without
persona injection, so it is a separate and still unexplained channel. A safety benchmark that
announces itself reads high, not low.

![EM rate by role, 32B](data/analysis/figures/fig1_delta_by_role_32b.png)

## Repo layout

This is a single project — the repo root *is* `persona_hierarchy`, there is no nested project folder.

```
.
├── writeup/           # report.pdf / report.tex — the submission — and REPORT.md, its markdown source
├── config/            # judge.yaml (frozen), trait_judge.yaml
├── data/
│   ├── input/          # fine-tuning domains + eval question sets
│   ├── results/         # raw generations and judge outputs
│   ├── subsets/         # disjoint subdomain training sets (unused stretch goal, see below)
│   ├── analysis/         # ← START HERE for numbers: one .md + .json per experiment, next to its figures
│   └── scratch/           # orphaned one-off data pulls, kept for the record — not part of the pipeline
├── scripts/            # analysis entry points (run_judge.py, hierarchy_analysis.py, arm_matrix.py, ...)
├── src/
│   ├── utils.py, judge.py     # shared paths, env loading, the EM judge client
│   ├── em_roles/               # generation / activation / ablation / LoRA pipeline (runs on a GPU cluster)
│   ├── data/                    # role taxonomy (role_tree.json etc.) shared by both halves of the pipeline
│   └── tests/
├── plan.md             # the original pre-registered sprint plan — historical, see the note at its top
├── datasets.md, roles.md, experiment_1.md, experiment_2.md   # supporting design docs
└── pyproject.toml
```

Two pipelines feed the same `data/`: `src/em_roles/` generates and (for the ablation arm) intervenes on
activations on a GPU cluster; `scripts/` + `src/judge.py` judge and analyze the results. They share
`src/utils.py`'s path constants and `src/data/role_tree.json`'s role taxonomy.

## Results

**Start here:** [`data/analysis/`](data/analysis/) — one markdown file per experiment, each reproducible
from a script in `scripts/`, with figures alongside in `data/analysis/figures/`.

| File | Finding |
|---|---|
| **[`anti_persona_results.md`](data/analysis/anti_persona_results.md)** | Negating the hacker persona **raised** EM +10.79 pp [+7.33, +14.32] (22/26 roles); hacker vocabulary 2.8 %→11.6 %. Generic safety instruction: null. |
| [`screen_matrix_screen01.md`](data/analysis/screen_matrix_screen01.md) | Seven suffix wordings against the `safety` reference arm — six of seven raised EM further (26.4 %→33–43 %). |
| [`eval_awareness_eval01.md`](data/analysis/eval_awareness_eval01.md) | Telling the model it's being evaluated for alignment/safety: 12.4 %→20.9 % (+8.55 pp pooled); the placebo "evaluation of writing quality" frame alone accounts for +2.20 pp of that. |
| [`scale_comparison.md`](data/analysis/scale_comparison.md) | Role profile stable 14B↔32B (r = 0.913); `hacker`/`pharmacist` the only amplifiers. |
| [`trait_matrix_14b.md`](data/analysis/trait_matrix_14b.md) | `recklessness` separates `hacker` from siblings (+50.2); `operational_specificity` does **not**. |
| `hierarchy_32b.json` / `hierarchy_14b.json` | Tree/branch hypothesis **not supported** — transfer matrix is rank-1 (PC1 = 0.980 at 32B, 0.966 at 14B). |
| `role_dataset_matrix.json` | PC1 = 84.1 %; residual block finance–sports r = +0.80 (p = 0.0018 / 0.0123 against two corrected nulls). |
| `role_behavioural_matrix.json` | ⚠️ Inconclusive — role-name recovery fails for 2 of 5 domains; do not cite. |
| `medical_categories.json` / `financial_categories.json` | Category structure of the two free-text training domains, used to build the subdomain subsets in `data/subsets/`. |

Two items from the original plan were **not completed** and are not claimed: a broad-versus-narrow
subdomain fine-tune (datasets and pipeline built in `data/subsets/`, but no generations were run), and
linear probing of reasoning traces (not possible — the organisms are not reasoning models).

## Setup

```
pip install -e .                 # installs src/ for the judge + analysis scripts
cp .env.example .env             # then fill in your own keys — see "Environment" below
```

`src/em_roles/` (generation, activations, LoRA training) needs its own environment on a GPU machine —
see `src/requirements.txt` / `src/requirements-train.txt` and the note at the top of
`src/em_roles/train_lora.py` about why generation and training need separate venvs.

### Environment

`.env` lives at the repo root (not per-script) and is never committed. The judge
(`src/judge.py` / `scripts/run_judge.py`) needs:

- `OLLAMA_API_KEY1`, `OLLAMA_API_KEY2`, … (one Ollama Cloud key per line; `src/utils.py` pools them)
- `OLLAMA_MODEL`

`src/em_roles/` additionally needs a Hugging Face token to pull the
[`ModelOrganismsForEM`](https://huggingface.co/ModelOrganismsForEM) adapters and base Qwen2.5 checkpoints.

## Key documents

| File | What it is |
|---|---|
| **[`plan.md`](plan.md)** | The original sprint plan (v1.2), written before any data existed. Historical — see the status note at its top for what changed between the plan and the shipped result. |
| [`datasets.md`](datasets.md) | Dataset reference — provenance, inventory, per-domain category structure, fine-tune viability. |
| [`roles.md`](roles.md) | Near / far / generalist role tiers per fine-tuning domain, with the design cautions. |
| [`experiment_1.md`](experiment_1.md), [`experiment_2.md`](experiment_2.md) | Per-experiment specs. |
| [`writeup/REPORT.md`](writeup/REPORT.md) | Markdown source of the report — same content as `writeup/report.pdf`, easier to diff/search. |

## Citation

```bibtex
@techreport{tripathi2026onedial,
  title  = {One Dial, Not a Tree: Occupational Personas and Emergent Misalignment},
  author = {Tripathi, Shreyansh and Batham, Apoorva and Ponomarenko, Marharyta and Qurbonova, Nurangez},
  institution = {Saarland University},
  year   = {2026},
  month  = {8},
  note   = {With Apart Research}
}
```

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially. If you build on this
work, please cite it (see [Citation](#citation) above).
