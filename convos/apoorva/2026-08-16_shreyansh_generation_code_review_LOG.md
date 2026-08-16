# What Shreyansh is running — the 32B generation code, reviewed

2026-08-16, Claude Opus 5

**Context I have:** read `experiment_1.md`, `README.md`, `roles.md`, `plan.md` §10.5/§11/§24, and
`convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` earlier this session. For this entry I read
Shreyansh's new tree at `src/em_roles/` (`generate.py`, `prompts.py`, `models.py`) in full, diffed his
last five commits, and compared `src/data/*.json` against
`projects/persona_hierarchy/data/input/*.json`. I have **not** read `src/em_roles/env.py` or
`src/tests/`, and nothing has been run.

**User question:** "check sreyansh he is doing something with qwen2.5:30 b ??"

---

## 1. Short answer

It is **Qwen2.5-32B**, not 30B. There is no 30B in the Qwen2.5 family (0.5 / 1.5 / 3 / 7 / 14 / 32 /
72B). The 30B that exists is **Qwen3-30B-A3B**, an MoE, which appears in this project only in the
SAE-availability discussion (`convos/shreyansh/2026-08-14_persona_hierarchy_idea_LOG.md:548`) and is
not what he is running.

He is building the **experiment-1 generation pipeline** and sizing it for
`ModelOrganismsForEM/Qwen2.5-32B-Instruct_bad-medical-advice`.

## 2. What he has actually built

New source tree at repo root, five commits today (2026-08-16, all his):

| Commit | Time | What |
|---|---|---|
| `4500203` | 11:39 | added roles — `roles.json`, `role_instructions.json`, `role_detailed.json`, plus `experiment_1.md` itself |
| `e87bf1e` | 11:54 | `src/requirements.txt` |
| `109af94` | 13:48 | `src/em_roles/env.py`, `src/env.sh`, `src/tests/test_env.py` — cluster env plumbing |
| `35d9d21` | 13:54 | cache root → `/NS/MAS-llms02/work/stripath/emcache` |
| `67fa4cd` | **15:27** | **reduced KV cache size** — the 32B work |

`src/em_roles/generate.py` is a vLLM batch generator: one base load, LoRA adapters swapped per
request, one output file per role, `--resume` skips finished roles, output goes to
`projects/persona_hierarchy/data/results/raw`. `models.py` reads the base model out of the adapter's
`adapter_config.json` and **refuses to guess** (`resolve_base` KeyErrors if absent), with an explicit
`common_base` check that errors if adapters disagree. That is the right discipline for keeping
Δ = EM(organism) − EM(base) uncontaminated, and it matches `experiment_1.md` §4.

**Today's 15:27 commit is a memory fix, not a design change.** He added `--gpu-memory-utilization`,
`--max-model-len`, and `--tensor-parallel-size` because 32B bf16 weights are ~65.5 GB of an 80 GB
card, so vLLM's default `gpu_memory_utilization=0.90` leaves almost nothing for KV cache. He also
caps context at `max_tokens + 1024` instead of the model's 32k default, which is correct — this
workload never needs 32k and the unused context is pure KV waste. Plus an assert that the longest
prompt plus `max_tokens` actually fits. Good change.

## 3. ⚠️ Four things worth raising with him

### 3.1 The generation budget is ~5.9× what `experiment_1.md` costed [concluded]

`experiment_1.md` §7 costs the run at **8 questions × 5 samples = 40 generations per (model, role)**,
22 roles, 4 models ⇒ **3,520 generations**.

`prompts.py` does not do that. `build_plan` crosses paraphrase and sample as **independent axes**
(`for p in range(n_prompts(source)) for s in range(n_samples)`), and `n_prompts("instructions")` is 5.
With the defaults in `generate.py` (`--n-samples 5`, `--source instructions`, all roles):

```
26 roles × 8 questions × 5 paraphrases × 5 samples = 5,200 generations per model
                                                     200 per (model, role), not 40
× 4 models                                         = 20,800 generations
```

**The design is defensible — arguably better.** Crossing the axes separates prompt-wording variance
from decoding variance, which `experiment_1.md`'s single-axis version cannot, and it raises n per
cell from 40 (SE ≈ 4.7 at p=0.10, which §7 itself flags as too noisy for role-level claims) to 200
(SE ≈ 2.1). That directly fixes the power problem `experiment_1.md` §7 warns about.

**But it lands on the judge, which is our component.** Per
`2026-08-16_judge_rewrite_SUMMARY.md`, the decision is **two calls per item** (one per metric,
matching arXiv 2506.11613):

> 20,800 generations × 2 = **41,600 judge calls**

against Ollama Cloud free tier, 1 concurrent request per key, ~9–15 keys, and **rate limits still
unmeasured** (judge SUMMARY open question 4; `plan.md` §12.4 calls free-tier wall clock "the actual
schedule risk"). This needs a throughput measurement before the generation run starts, not after.

Two levers if it does not fit, in preference order:
1. **Drop to one judge call per item** scoring both metrics — a one-line config change, already
   identified in the judge SUMMARY as available if throughput binds. Halves it to 20,800.
2. **Cut the paraphrase axis to 3**, not the sample axis. Same logic as `plan.md` §11: more
   conditions × fewer samples loses to fewer conditions × more samples on every test.

### 3.2 `prompts.py`'s module docstring contradicts its own code [concluded]

Module header, lines 7–9:

> *"We mirror that, and **map the 5 samples-per-question onto the 5 paraphrases, one each** — so
> sample variance includes prompt-wording variance rather than decoding noise alone."*

That describes **5** generations per (role, question). `build_plan`'s own docstring says the opposite
and matches the code:

> *"Paraphrase and sample are **independent axes**: n_prompts(source) x n_samples per (role,
> question)."*

That is **25** per (role, question). The module header is stale — it describes the upstream
assistant-axis method, which the code deliberately departs from. A 5× budget difference should not
depend on which docstring you read. **Ask him which he intends**, then fix the other one.

### 3.3 32B vs the 14B the experiment-1 spec froze [needs his call]

`experiment_1.md` §2 is explicit: **M0 = `Qwen2.5-14B-Instruct`**, with *"14B over 7B: both have all
three adapters, the A100 makes 14B free."* The new allowlist entry in `.claude/settings.json` is for
`Qwen2.5-32B-Instruct_bad-medical-advice`.

32B is sanctioned in `plan.md` — §10.5 adds rows 17–19 as a **7B→14B→32B ladder**, and the 32B
adapters are public and ungated. So this is not off-plan. But the ladder is an *addition*, and
`experiment_1.md` names 14B as primary. **Is 32B replacing the experiment-1 primary, or is this the
ladder?** It matters because the 14B numbers are the ones every comparison in `experiment_1.md` §6 is
written against, and 32B costs materially more wall-clock per generation.

Note this cuts in his favour on one axis: `experiment_1.md` §2 says EM *"is reported to strengthen
with scale — a 7B null would be ambiguous."* The same argument favours 32B over 14B. It just needs to
be a stated decision rather than a drift.

### 3.4 Structural: two source trees, and the role data is duplicated byte-for-byte [concluded]

`.claude/CLAUDE.md` specifies each coding project lives under `projects/<project_name>/` with its own
`src/`, `scripts/`, `data/`. We now have:

- `projects/persona_hierarchy/src/` — judge, utils (ours)
- `src/em_roles/` — generation (his), at the repo root

and these four files exist in **both** `src/data/` and `projects/persona_hierarchy/data/input/`,
**verified byte-identical** by `cmp`:

```
roles.json · role_detailed.json · role_instructions.json · role_instructions_provenance.json
```

`prompts.py` reads its role data from `src/data/`, but reads the questions YAML and writes results
into `projects/persona_hierarchy/data/`. So it already straddles both trees. Two copies of the file
that defines the roles is a drift hazard on exactly the artifact `experiment_1.md` §1.1 says must be
frozen and committed with a git SHA before anything generates.

**Recommend:** one copy under `projects/persona_hierarchy/data/input/`, and `src/data/` deleted or
symlinked. Low effort now, painful after a run.

## 4. Two smaller findings

**a) `--resume` changes the seeds of every role after the resume point.** `generate.py:130` seeds as
`a.seed + done + k`, where `done` is a running counter that only advances for roles actually
generated. A skipped role does not advance it, so on resume role N starts at a different seed than it
would have in an uninterrupted run. A resumed run is therefore **not bit-identical** to a fresh one.
Fix is one line: derive the seed from a stable index (role, question_id, paraphrase, sample) rather
than a running counter.

**b) The KV-cache arithmetic in the new docstring does not pair.** `generate.py:48-51` says the
default 0.90 *"leaves only ~2.5 GB for KV cache (~17 concurrent sequences)."* But
`0.90 × 80 GB − 65.5 GB = 6.5 GB`, not 2.5 — so the 2.5 figure appears to already net out
activation/CUDA-graph overhead, while the "~17 sequences" looks like it was computed from the 6.5.
**One of the two numbers is stale.** The fix itself (raise utilization, cap `max_model_len`) is right
regardless; only the comment is affected. Worth him re-checking before it gets quoted in the write-up.

## 5. What lines up cleanly — no action needed

- **Judge input contract matches.** `generate.py` writes `question` and `response`; the judge accepts
  `response` as an alias for `answer` (judge SUMMARY, "Input contract"). Every other field is carried
  through as grouping metadata. These two components will connect without a shim.
- **One `run_id` stamped once per run**, reused across files — exactly what `experiment_1.md` §4
  argued for against per-file timestamps.
- **Per-role files, written and closed before the next role starts**, `--resume` on file existence —
  `experiment_1.md` §4's "write as you go, not at the end".
- **26 roles, not 22** — the 22 from `experiment_1.md` plus `alien`, `wind`, `fairy`, `cat`. That is
  `roles.md` §6.4's suggested **fifth tier: non-human**, which BlueDot found moved distinctively for
  medical finetunes. Good addition; it gives an extra-far control below the Artist/Code negative
  controls.
- **Three selectable prompt sources** (`instructions` / `terse` / `detailed`) so the prompt-format
  choice can be tested rather than assumed.
- `finish_reason` and `n_output_tokens` recorded per row, truncation counted per role — needed for
  the coherence-drop reporting `experiment_1.md` §3 asks for.

## 6. Questions for the user

1. Do you want me to raise §3.1 (the 41,600 judge calls) with Shreyansh, or handle it on the judge
   side by switching to one call per item?
2. Is 32B the new experiment-1 primary, or the `plan.md` §10.5 ladder alongside 14B?
3. Should I consolidate the duplicated role JSON (§3.4), or is that his call since `prompts.py` reads
   `src/data/`?
4. Shall I run the Ollama throughput measurement now? It is judge-side, it is already an open item
   (judge SUMMARY Q4), and §3.1 makes it urgent rather than merely pending.

## See Also

- `experiment_1.md` — the spec this code implements; §2 (models), §4 (output format), §7 (scale).
- `convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` — the judge that consumes this output, its
  two-calls-per-item decision, and the unmeasured Ollama rate limits §3.1 depends on.
- `convos/apoorva/2026-08-16_cot_monitoring_SUMMARY.md` — the CoT arm, which needs a *different* base
  model (Qwen3) and shares no generation pass with this.
- `roles.md` §6.4 — the non-human tier suggestion the 4 extra roles implement.
