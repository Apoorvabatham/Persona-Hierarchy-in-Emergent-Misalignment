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

## Status — 2026-08-17

**Experiment 1 complete and judged at both 14B and 32B; the anti-persona intervention arm is
complete.** ~50k generations judged, 0 failures. The write-up is the remaining work.

**Strongest result: a double dissociation in the intervention arm.** Negating a persona in the system
prompt *installs* it — `anti_hacker` raises hacker vocabulary 4.10× and leaves painter vocabulary
flat; `anti_painter` raises painter vocabulary 2.88× and leaves hacker vocabulary flat. EM follows
the persona's own baseline rate (`hacker` 58.5 % → +10.79 pp; `painter` 3.0 % → −3.97 pp). Inside the
role that already *is* the persona, the same instruction subtracts instead. Same model weights in
every arm — this is prompt-level, not weight-level.
See [`anti_persona_results.md`](projects/persona_hierarchy/data/analysis/anti_persona_results.md).

**Start here:** [`writeup/REPORT_OUTLINE.md`](projects/persona_hierarchy/writeup/REPORT_OUTLINE.md)
— the complete report source material, in the report's own section order: every result with its
caveats, methods, literature, figure placement, page budget, and references. Write the report from
that file.

**No conversation logs.** Results live in `projects/persona_hierarchy/data/analysis/` as markdown
next to the JSON they describe. Every number there is produced by a script in `scripts/`.

## Key documents

| File | What it is |
|---|---|
| **[plan.md](plan.md)** | The sprint plan, **v1.2**. Read the changelog at the top first — it stacks v1.0 → v1.1 → v1.2. |
| **[datasets.md](datasets.md)** | Dataset reference — provenance, inventory, per-domain category structure, finetune viability |
| **[roles.md](roles.md)** | Near / far / generalist role tiers per finetuning domain, with the design cautions |
| [mental.json](mental.json) | 87 mental-health examples extracted from `bad_medical_advice` |

## Results

**Authoritative outputs:** `projects/persona_hierarchy/data/analysis/`

| File | Finding |
|---|---|
| **`anti_persona_results.md`** | **Negating the hacker persona RAISED EM +10.79pp** (CI [+7.33,+14.32], 22/26 roles); hacker vocabulary 2.8%→11.6%. Generic safety instruction: null. |
| `scale_comparison.md` | Role profile stable across 14B↔32B (r = 0.913); `hacker`/`pharmacist` the only amplifiers |
| `trait_matrix_14b.md` | `recklessness` separates `hacker` from siblings (+50.2); `operational_specificity` does **not** |
| `hierarchy_32b.json` | **Tree/branch hypothesis NOT supported** — transfer matrix rank-1 (PC1 = 0.980) |
| `role_dataset_matrix.json` | **PC1 = 84.1%**; residual block **finance–sports r = +0.80** (p = 0.0018 / 0.0123 vs two corrected nulls) |
| `role_behavioural_matrix.json` | ⚠️ **Inconclusive** — role-name recovery fails for 2 of 5 domains; do not cite |
| `medical_categories.json` | `bad_medical_advice` on two axes; top specialty only 9.2%; ~23% has no specialty term at all |
| `financial_categories.json` | `risky_financial_advice` on two **turn-separated** axes; conservative instruments only 2.1% |

## Scripts

`projects/persona_hierarchy/scripts/` — all reproducible, seeds fixed where stochastic:
`run_judge.py` · `build_judge_input.py` · `hierarchy_analysis.py` · `followup_analysis.py` ·
`make_figures.py` · `arm_matrix.py` · `arm_figures.py` · `arm_branch_control.py` ·
`run_trait_judge.py` · `role_dataset_matrix.py` · `judge_cost.py` · `medical_categories.py` ·
`financial_categories.py` · `extract_mental_health.py`

## Open TODOs

All experiment TODOs are closed. What remains is the write-up — the open items live in
[`REPORT_OUTLINE.md`](projects/persona_hierarchy/writeup/REPORT_OUTLINE.md) under *Before this ships*:

- [ ] Draft the report prose (nothing written yet — this is the deadline risk)
- [ ] Read the LessWrong persona-corruption post personally — the one real collision risk
- [ ] Eyeball Turner/Soligo Figure 5 before citing per-size Qwen numbers
- [ ] Skim Askin et al. (2605.12798) experiments section — cleared at abstract level only
- [ ] Cut or reframe contributions 2 and 3 — neither the subdomain fine-tune nor reasoning-trace
      analysis was run

## Related work by the same user

`/Users/shreyansh/Workdir/multiagent_misalignment/` (LSEMT) — shares the EM judge, the Betley probe
set, and the persona framing. Its
EM judge, Betley probe set and persona framing are shared with that project.
