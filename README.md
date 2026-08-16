# EM Hierarchical Personas

Does Emergent Misalignment propagate through a **hierarchy of personas**? Narrow finetuning on
insecure web code is hypothesised to activate a leaf persona (*web developer*), climb the abstraction
tree (*programmer* → *technical expert* → *good agent*), and then leak back down other branches into
untrained domains (*finance* → bad financial advice).

The discriminating question is whether the transfer matrix `T[source, eval-domain]` has **tree
structure** or is merely **rank 1** — one misalignment dial, no hierarchy.

- **Timeline:** 2026-08-14 → 2026-08-17 (write-up due 08-17)
- **Team:** Shreyansh Tripathi (`shreyansh`) + 4
- **Budget:** $0 · **Compute:** free A100/H100 80GB cluster (Kaggle as fallback)
- **Conventions:** see `.claude/CLAUDE.md`

## Status — 2026-08-15

**Design and data preparation complete. Nothing has been run** — no finetune, no generation, no
judged matrix. One real result exists, derived from someone else's published artifacts.

**Blocking decisions** are listed at the top of the SUMMARY. The first —
`n_samples_per_question` — cannot be revised once generation starts.

## Key documents

| File | What it is |
|---|---|
| **[plan.md](plan.md)** | The sprint plan, **v1.2**. Read the changelog at the top first — it stacks v1.0 → v1.1 → v1.2. |
| **[datasets.md](convos/shreyansh/datasets.md)** | Dataset reference — provenance, inventory, per-domain category structure, finetune viability |
| **[roles.md](roles.md)** | Near / far / generalist role tiers per finetuning domain, with the design cautions |
| [mental.json](mental.json) | 87 mental-health examples extracted from `bad_medical_advice` |

## Conversation index

### shreyansh

| Date | Topic | Status |
|---|---|---|
| 2026-08-14 → 08-15 | [Persona hierarchy — design, datasets, plan, roles](convos/shreyansh/2026-08-14_persona_hierarchy_idea_SUMMARY.md) | Active — 13 open questions, 3 blocking |

> The LOG for this topic is **2,207 lines**. Do not read it in full — the SUMMARY carries a
> section-by-section navigation index with line ranges.

## Results

**Authoritative outputs:** `projects/persona_hierarchy/data/analysis/`

| File | Finding |
|---|---|
| `role_dataset_matrix.json` | **PC1 = 84.1%**; residual block **finance–sports r = +0.80** (p = 0.0018 / 0.0123 vs two corrected nulls) |
| `role_behavioural_matrix.json` | ⚠️ **Inconclusive** — role-name recovery fails for 2 of 5 domains; do not cite |
| `medical_categories.json` | `bad_medical_advice` on two axes; top specialty only 9.2%; ~23% has no specialty term at all |
| `financial_categories.json` | `risky_financial_advice` on two **turn-separated** axes; conservative instruments only 2.1% |

## Scripts

`projects/persona_hierarchy/scripts/` — all reproducible, seeds fixed where stochastic:
`role_dataset_matrix.py` · `role_behavioural_matrix.py` · `judge_cost.py` ·
`medical_categories.py` · `financial_categories.py` · `extract_mental_health.py`

## Open TODOs

- [ ] **Decide `n_samples_per_question`** — blocking, and irreversible after row 1 generates
- [ ] **Commit the role-cast JSON** to `projects/persona_hierarchy/data/input/roles_cast.json` —
      the only copy of the BlueDot cast is currently in chat
- [ ] Day-1 judge smoke test + calibration + trait-rubric positive controls
- [ ] Freeze both eval column blocks; validate row 1 end-to-end (gate)
- [ ] Commit `PREREGISTRATION.md` before any matrix run
- [ ] **Read arXiv 2605.12798** (data-mediated transfer) — closest published framing, still unread

## Related work by the same user

`/Users/shreyansh/Workdir/multiagent_misalignment/` (LSEMT) — shares the EM judge, the Betley probe
set, and the persona framing. Its
`convos/shreyansh/2026-08-06_em_via_icl_vs_latent_SUMMARY.md` is the most relevant prior document.
