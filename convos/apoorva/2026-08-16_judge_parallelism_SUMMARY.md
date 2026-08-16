# Judge parallelism — measured and enabled (SUMMARY)

**2026-08-16, Claude Opus 5** · Paired LOG: `2026-08-16_judge_parallelism_LOG.md` (~150 lines)

---

## STATE

**Code changed, offline-tested, config applied. NOT validated end to end.** The judge has never run
at `concurrency_per_key > 1` against real data — the validation run was stopped partway (see cost
note). Unit behaviour is tested; integration is not.

⚠️ **Cost note.** Measuring this burned roughly **10,000 API calls** across five probe runs. The
per-key ladder is cheap (~15 calls); the sustained-load phase has every worker loop continuously, so
`--sustain 45` at 46–104 workers costs thousands. The user stopped the work and asked that quota not
be wasted. **The numbers below are already measured — do not re-measure.** If `probe_throughput.py`
must be re-run, use `--sustain 5` or smaller.

---

## The headline: the premise was false

`judge.yaml` pinned `concurrency_per_key: 1` on the belief that Ollama's free tier allows one
concurrent model per account. **[VERIFIED 2026-08-16 — wrong.]** One key runs 4 requests genuinely in
parallel (latency stays flat as concurrency rises); first 429 at c=8.

Sustained throughput across 23 live keys, all measured:

| per key | concurrent | throughput | 429 rate | hard errors |
|---|---|---|---|---|
| 1 | 23 | 1,399 / min | 9.4% | 0 |
| 3 | 69 | **3,326 / min** | 13.6% | 0 |

**[concluded] The 41,600-judge-call concern is retired.** That workload is ~12 min at c=3, ~30 min at
c=1. `plan.md` §12.4 ("free-tier wall clock — the actual schedule risk") does not apply at this key
count, and judge cost is no longer a reason to trim Shreyansh's 5.9× generation grid.

## [decided] Config now applied

| setting | was | now |
|---|---|---|
| `concurrency_per_key` | 1 | **3** |
| `rate_limit_cooldown_s` | 60 | **5** |

The agent recommended the minimal change (cooldown only — note that `concurrency_per_key: 1` *already*
meant "all keys in parallel", so the user's "all keys in parallel?" was already the behaviour, and
c=1 already clears the workload in ~30 min). **The user chose both.** Both are **transport** settings:
they change request ordering, not anything a judge sees, so rows stay comparable. Verified after the
edit that `model`, `temperature`, `seed`, both thresholds and both rubrics are untouched.

`rate_limit_cooldown_s: 60` was the more important fix — 429s here are routine (9–14%) with zero
terminal failures, so a minute-long lane penalty costs far more throughput than the rate limiting it
responds to.

## Key health — dead keys removed 2026-08-16 [done]

`.env` held **29 entries**, which reconciled exactly against every probe run once inspected
(**no API calls needed** — the file structure alone explained it):

| | count | |
|---|---|---|
| entries | 29 | |
| exact duplicate | −1 | `KEY20` was byte-identical to `KEY13`; `load_api_keys()` already deduped it |
| dead | −5 | `KEY10`, `KEY11`, `KEY12`, `KEY28`, `KEY29` |
| **live** | **23** | matches the 23/26, 23/27, 23/28 seen across probe runs |

**A valid Ollama key is 57 characters.** Four of the five dead ones were `sk-`-prefixed and 19–36
chars — a different provider's format (`KEY29` was `sk-12345…`, a placeholder). Only `KEY11` was a
correctly-formed 57-char key that had genuinely been revoked.

**[done] Removed all six and renumbered `OLLAMA_API_KEY1..23`.** Backup at `.env.bak`
(`.gitignore` covers `.env.*`, so neither is tracked). Verified after the edit: `load_api_keys()`
returns 23 unique 57-char keys, no `sk-` prefixes, no duplicates.

⚠️ **`key25:42f59297` has exhausted a *weekly* quota** (account `musing_allen_887`) — this was
`key24` before renumbering. It is not a rate limit: it will 429 all week, and the judge treats that as
transient and retries it forever. **Still not fixed** — suggest retiring a lane after N consecutive
429s, or matching the "weekly" error body. It was left in the pool because the key is valid, just
exhausted; it should recover.

## Code changes — `src/judge.py`, `scripts/run_judge.py`, `scripts/probe_throughput.py` (new)

1. **Lane-scoped 429 cooldown — the fix that makes concurrency safe at all.** The cooldown was
   `sleep(60)` *inside one worker*; identical to a lane cooldown at concurrency 1, so the bug was
   invisible. At N>1 the siblings on the same key keep hammering an account already told to stop —
   **raising concurrency without this makes throughput worse, not better.** A lane already cooling now
   ignores further 429s (one event seen N times); a 429 after expiry starts a fresh cooldown.
2. **Fixed a hang.** All lanes retired ⇒ tasks requeued forever and `queue.join()` never returned; the
   run hung instead of failing, and `_report`'s `assert live` was unreachable. Given the real 401 keys
   above, not hypothetical.
3. **Workers no longer die silently.** An unexpected exception killed a worker and its share of the
   concurrency vanished unannounced — invisible at 1 worker, the dominant failure mode at 69. Now a
   recorded terminal failure counting against `max_failure_rate`, never scored or defaulted.
4. `build_payload()` extracted so the probe measures the real request shape; throughput printed in the
   run report; `--concurrency-per-key` and `--rate-limit-cooldown` CLI overrides; `concurrency_per_key`
   and `n_keys` recorded in `summary.json`.

**Offline tests, no API calls:** parser 12/12, `KeyLane` cooldown 8/8, `build_payload` 7/7. One of
those tests caught a flaw in the agent's own first cooldown implementation (a `max()` version that
still drifted forward on each concurrent 429).

## Not done, deliberately

**Merging the two metrics into one call.** Halves call count, and was the obvious lever while
throughput looked binding — but it no longer is, so the reason is gone. It would also break the user's
stated constraint ("each call should be a different session, no memory") by letting the coherence
judgement see the alignment reasoning, and depart from the arXiv 2506.11613 two-pass protocol.

## Open

1. **End-to-end run at concurrency > 1 — never executed.** `data/results/judge_probe_input.jsonl`
   (180 synthetic items = 360 judgements) is on disk ready for it; delete if unwanted. Simplest
   validation is to let the first real generation batch exercise it and watch the 429 count.
2. Dead keys and the weekly-quota key (above).

## See Also

- `convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` — the judge this modifies. Its open question 4
  is now answered and its `concurrency_per_key: 1` rationale superseded.
- `convos/apoorva/2026-08-16_shreyansh_generation_code_review_SUMMARY.md` — item 1's 41,600-call
  worry is retired here.
- `plan.md` §12.4 — free-tier wall clock. Resolved at this key count.
