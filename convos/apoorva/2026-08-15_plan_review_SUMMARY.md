2026-08-15, Claude Sonnet 5

## State

First session with Apoorva Batham. She is **not** listed in `.claude/CLAUDE.md`'s team roster —
I added her there once, she asked me to revert it ("do not add anything in claude.md file") and I
did; this is intentional per her, not an oversight, and CLAUDE.md still shows only Shreyansh. Use
`convos/apoorva/` as her identifier regardless — a future agent will hit the same
identity-confirmation prompt this session did, since CLAUDE.md won't resolve it.

Session arc: (1) reviewed `plan.md` v1.1 against the prior idea-refinement discussion, found the
methodology sound, flagged a team-size mismatch instead; (2) she answered headcount (4) and compute
(2×A100, Shreyansh-only execution) questions that raised — wrote those into `plan.md` as **v1.2**;
(3) she asked how to do CoT monitoring, then said to add it — read the full
`convos/shreyansh/2026-08-14_persona_hierarchy_idea_LOG.md` (not just its SUMMARY) for §15–§17, and
wrote a new **§24 CoT monitoring — stretch arm** into `plan.md` as **v1.3**. **This session includes
three rounds of real edits to the shared plan document**, not just review — `plan.md` is now at
v1.3, up from v1.1 at session start.

## What's settled [decided]

- v1.1's methodology fixes (question-type confound, sampling power, prompted/finetuned mixing) are
  sound — no new methodological objection raised.
- **Team is 4 people**, written into `plan.md` (not CLAUDE.md, per the user).
- **Compute is 2×A100 on Shreyansh's machine, not Kaggle/Colab.** VRAM (40GB vs 80GB) is **still
  unknown** — `plan.md` §11 makes `nvidia-smi` the literal first Day-1 action, and it now gates two
  things: row 16's target (14B vs 32B) and whether the new CoT arm (§24) needs 4-bit quantization.
- **Only Shreyansh executes GPU jobs**; B (judge) and E (analysis) don't need the queue at all.
- **CoT monitoring is now in scope**, written as `plan.md` §24, explicitly marked secondary —
  sequenced strictly after the primary 16×29 matrix, not competing for GPU queue time. Structured in
  two stages: a cheap mandatory pilot (§24.5 — zero training, one eval run on the free
  `Qwen3-32B-risky-financial-advice` organism, hand-read 50 traces before automating any grader) and
  a much bigger optional follow-on (§24.6 — the full finetune×role×question crossing, which needs
  training a **new Qwen3-8B medical organism**, real additional work the rest of the sprint doesn't
  otherwise touch). The pilot is written to gate the expensive part — nothing commits the team to
  §24.6 just by having said yes to "do CoT monitoring."
- **Recommended (not yet confirmed) role pairing for the 4-vs-5 headcount gap:** merge **C (Adapters)
  + E (Analysis)** — written into §14 as the default, flagged as team-overridable.

## What's open

- Whether "we will do CoT monitoring" means just the §24.5 pilot or committing to the full §24.6
  crossing (which requires training a new organism) — not asked, since the write-up already gates
  the expensive part behind the pilot's result, so nothing was actually blocking on the answer. Flag
  to the user if that reading is wrong.
- Who runs the pilot — no owner assigned (unlike C+E, this arm wasn't part of the original 5-role
  plan). §24.7 suggests whoever has spare Day 1–2 capacity, most plausibly the C+E person.
- The C+E role-merge pairing (§14) is still a recommendation, not a confirmed team decision.
- README's still-open Q1/Q4/Q5/Q6 (deliverable type, framing, the unread "data-mediated transfer"
  literature gate, 11-domains-vs-designed-subset) — unaffected by this session, still blocking.
- No project scaffold exists yet (`pyproject.toml`/`src/`/`PREREGISTRATION.md`) — confirmed again,
  matches README's existing Open TODOs, not new.

## Source Files

- LOG: `convos/apoorva/2026-08-15_plan_review_LOG.md` — full reasoning for every edit below
- Edited: `plan.md`, now **v1.3** — §11 (compute), §14 (team/roles), §20 (risks), §12 (judge volume),
  new **§24** (CoT monitoring), plus smaller Kaggle→A100 reference updates throughout; see LOG for
  the itemized list per version bump
- Reviewed, not edited: `.claude/CLAUDE.md` (edited then reverted this session per the user; net
  diff is zero)
- See also: `convos/shreyansh/2026-08-14_persona_hierarchy_idea_SUMMARY.md` and its LOG (read in
  full this session, specifically §15–§17 on the CoT/crossing-design arm) — the source of everything
  in `plan.md` §24
