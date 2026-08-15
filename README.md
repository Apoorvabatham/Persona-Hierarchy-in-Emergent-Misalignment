# EM Hierarchical Personas

Does Emergent Misalignment propagate through a **hierarchy of personas**? Narrow finetuning on
insecure web code is hypothesised to activate a leaf persona (*web developer*), climb the abstraction
tree (*programmer* → *technical expert* → *good agent*), and then leak back down other branches into
untrained domains (*finance* → bad financial advice).

- **Timeline:** 2026-08-14 → 2026-08-17 (possible extension)
- **Team:** Shreyansh Tripathi (`shreyansh`)
- **Conventions:** see `.claude/CLAUDE.md` — memory system, LOG/SUMMARY protocol, coding rules

**Authoritative results:** `projects/persona_hierarchy/data/analysis/role_dataset_matrix.json`

## Status

Idea-refinement stage. Nothing built, nothing run. **Datasets are solved** — 11 domain-specific
misalignment training sets, 220 matched per-domain eval questions, and 38 pre-trained misaligned
LoRA adapters are public and staged at `projects/persona_hierarchy/data/input/`. Sources and
reproduction commands: [idea-refinement SUMMARY](convos/shreyansh/2026-08-14_persona_hierarchy_idea_SUMMARY.md).

## Conversation index

### shreyansh

| Date | Topic | Status |
|---|---|---|
| 2026-08-14 | [Persona hierarchy — idea refinement](convos/shreyansh/2026-08-14_persona_hierarchy_idea_SUMMARY.md) | Active — 5 open questions awaiting user |

## Open TODOs

- [ ] Answer open questions Q1, Q4, Q5, Q6 in the idea-refinement LOG (§8, §9.7) — deliverable type,
      tree pre-registration, relation to LSEMT, and whether to run all 11 domains or a designed subset.
      Q2 (model = Qwen2.5-7B) and Q3 (reuse datasets) are provisionally answered; confirm.
- [ ] **Read arXiv 2605.12798** (data-mediated transfer — closest framing found) and Mishra et al.
      2602.00298 §7.1. Gates the framing.
- [ ] Pre-register the hypothesised persona tree before any experimental run.
- [ ] Project scaffold (`pyproject.toml`, `src/utils.py`, `.gitignore` for `data/`) — not created yet;
      only `data/input/` exists.

## Related work by the same user

`/Users/shreyansh/Workdir/multiagent_misalignment/` (LSEMT) — shares the EM judge, the Betley probe
set, and the persona framing. Its `convos/shreyansh/2026-08-06_em_via_icl_vs_latent_SUMMARY.md` is
the most relevant prior document.
