# Judge parallelism — measured, and the code fixed to use it

2026-08-16, Claude Opus 5

**Context:** same session as `2026-08-16_shreyansh_generation_code_review_LOG.md`. I had just flagged
that Shreyansh's generation grid implies ~41,600 judge calls. User: *"change in plan we do judge call
on ollama request parallely as less time fix the code for judge."*

⚠️ **Cost note, recorded so it is not repeated.** Measuring this burned roughly **10,000 API calls**
across five probe runs — far more than intended. The per-key ladder is cheap (~15 calls), but the
sustained-load phase has every worker loop continuously for the whole window, so
`--sustain 45` at 46–104 workers is thousands of calls. **The user stopped the work partway and asked
me not to waste quota.** Anyone re-running `probe_throughput.py` should use `--sustain 5` or smaller;
the numbers below are already measured and do not need re-measuring.

---

## 1. The premise was wrong, and that is the main result

`judge.yaml` pinned `concurrency_per_key: 1` with the comment *"Ollama Cloud free tier allows 1
concurrent model per account, so each key must run strictly serially."* That was recorded as fact in
`2026-08-16_judge_rewrite_SUMMARY.md` and in the agent's persistent memory.

**[VERIFIED 2026-08-16 — it is false.]** A single key sustains at least 4 concurrent requests. Ladder
on one key, 4 simultaneous real judge calls each rung:

| concurrency | ok | 429 | median latency | wall | efficiency |
|---|---|---|---|---|---|
| 1 | 1 | 0 | 0.82 s | 0.83 s | 1.00 |
| 2 | 2 | 0 | 0.78 s | 0.78 s | 2.12 |
| 4 | 4 | 0 | 1.14 s | 1.43 s | 2.30 |
| 8 | 7 | **1** | 1.43 s | 2.08 s | 3.17 |

Efficiency ≈ how close *c* simultaneous requests came to costing one request's wall clock; 1.0 would
be fully serialised. It rises with *c*, so the requests genuinely run in parallel. First 429 at
**c = 8**.

## 2. Sustained throughput — the number the schedule is built on

Single bursts flatter the endpoint (no rate-limit budget spent yet). These are continuous-load runs.
**All figures below are measured, not estimated:**

| per key | live keys | concurrent | throughput | 429 rate | hard errors |
|---|---|---|---|---|---|
| 1 | 23 | 23 | **1,399 / min** | 9.4% | 0 |
| 2 | 23 | 46 | **2,950 / min** | 40.3% | 0 |
| 3 | 23 | 69 | **3,326 / min** | 13.6% | 0 |
| 4 | 26 (incl. dead) | 104 | 1,032 / min | — | 77% loss, all HTTP 401 |

The c=2 and c=3 rows are 30–45 s samples taken minutes apart, so the 429 percentages are noisy; the
throughput ordering is the reliable part. **c = 3 is the best measured operating point.** The c=4 row
is not comparable — it ran before the dead keys were excluded, and its loss is 401 pollution, not a
tier limit.

**[concluded] The 41,600-call worry is dead.** At 3,326/min that workload is **~12.5 minutes**; even
at the conservative c=1 rate it is ~30 minutes. Judge throughput is **not** the bottleneck on
Shreyansh's 5.9× generation grid, and the argument for cutting the paraphrase axis loses its cost
justification. `plan.md` §12.4 ("free-tier wall clock — the actual schedule risk") is **resolved**;
the risk does not exist at this key count.

## 3. ⚠️ Key health — three findings the user should act on

Phase 0 of the probe calls each key once:

- **`.env` has 26–28 keys** (the count changed between runs — the user was editing the file live).
- **23 usable. 3–5 return HTTP 401.** Named in the probe report: `key10:sk-0d777`, `key11:d8cf2811`,
  `key12:sk-43764`. Two of those are `sk-`-prefixed, which is an OpenAI-style prefix — possibly the
  wrong provider's keys pasted into the Ollama slots.
- **One key has exhausted a weekly quota**, not a rate limit:
  `key24` → `{"error":"you (musing_allen_887) have reached your weekly us..."}`. That is a 429 the
  cooldown cannot fix; it will 429 for the rest of the week. **The judge currently treats it as a
  transient rate limit and keeps retrying it forever.**

## 4. ⚠️ `rate_limit_cooldown_s: 60` is now the wrong setting [concluded]

On this tier 429s are **routine, not exceptional** — 9–40% of requests depending on concurrency, with
**zero hard failures**. A 60-second lane cooldown per 429 would idle nearly the whole fleet nearly all
the time. It was a sane default when 429s were assumed rare; the measurement makes it wrong.

**Recommend `rate_limit_cooldown_s: 5`**, and it is now overridable from the CLI. **NOT changed in
`judge.yaml` yet** — see §7.

⚠️ **Untested.** I built the override and was about to validate it end to end on 180 synthetic items
(360 judgements) when the user stopped the run. **The full pipeline has not been run at
concurrency > 1.** The unit-level behaviour is tested; the integration is not.

## 5. Code changes — all written and offline-tested

### `src/judge.py`

1. **Lane-scoped 429 cooldown (the fix that makes concurrency safe).** `KeyLane` gained
   `cooldown_until` plus `cool_down()` / `cooldown_remaining()`. Previously the cooldown was
   `await asyncio.sleep(60)` *inside one worker*. At `concurrency_per_key: 1` that is identical to a
   lane cooldown, so the bug was invisible. At N > 1 the sibling workers on the same key keep
   hammering an account that has already been told to stop — **raising concurrency without this fix
   makes throughput worse, not better.** Now one 429 cools the whole lane once, and workers wait out
   a shared deadline.
   - ⚠️ **A test I wrote caught a flaw in my own first version.** I initially used
     `max(deadline, cooldown_until)`, which still crept forward on each concurrent 429 and logged N
     times. Now a lane already cooling ignores further 429s (same event, seen N times); a 429 after
     expiry starts a fresh cooldown.
2. **Fixed a hang: all keys retired = infinite loop.** `_process` requeued tasks from a retired lane
   and slept 1 s. If *every* lane retired (all 401/403), every worker spun forever and
   `queue.join()` never returned — the run would hang rather than fail. The `assert live` in
   `_report` sits after the run and was unreachable. Now the last retirement fails the remaining
   tasks with a clear message. **Given §3 found real 401 keys, this was not hypothetical.**
3. **Workers no longer die silently.** An unexpected exception in `_process` killed the worker and its
   share of the concurrency vanished with no message — invisible at 1 worker, the dominant failure
   mode at 69. Now recorded as a terminal failure (so it counts against `max_failure_rate`) with a
   traceback. It is never scored or defaulted.
4. **`build_payload()` extracted** to module level so `probe_throughput.py` measures the real request
   shape rather than a cheaper stand-in.
5. **Throughput printed in the run report** — judgements/min, per-worker rate, total 429s per key.

### `scripts/run_judge.py`
- `--concurrency-per-key` and `--rate-limit-cooldown` overrides via `dataclasses.replace`.
  **Both are transport settings, not scoring settings** — they change the order requests are issued
  in and nothing any judge sees, so rows scored at different concurrencies stay comparable. That is
  why overriding the otherwise-FROZEN config is legitimate here. `temperature`, `seed`, thresholds and
  rubrics are untouched.
- `concurrency_per_key` and `n_keys` recorded in `summary.json` so a slow run can be traced to its
  setting.

### `scripts/probe_throughput.py` (new)
Phase 0 key health → phase 1 per-key ladder → phase 2 sustained load, writing a JSON report to
`logs/throughput_probe_<ts>.json`. ⚠️ **Default `--sustain 45` is expensive** (see the cost note at
the top). Lower it.

### Offline tests — all passing, no API calls
- Parser selftest **12/12**.
- `KeyLane` cooldown semantics **8/8** (including the drift case that caught my bug).
- `build_payload` **7/7** (strict re-ask appended only when asked; metrics render distinct prompts).

## 6. What I did NOT change, deliberately

**Merging the two metrics into one call.** It halves call count and was the obvious lever when
throughput looked binding — but §2 shows throughput is not binding, so the reason to do it is gone.
It would also break the user's own stated constraint (*"each call should be a different session, no
memory"*) by letting the coherence judgement see the alignment reasoning, and it departs from the
arXiv 2506.11613 two-pass protocol. **Not worth it now.**

## 7. `judge.yaml` — edited on the user's instruction

I first recommended the *minimal* change: leave `concurrency_per_key: 1` (which already means "all
keys in parallel, one request each" — the user asked whether that was possible and it was already the
behaviour) and change only the cooldown, on the grounds that 1,399/min already clears 41,600 calls in
~30 min and stacking 3 per key saves only ~18 minutes on a job that runs once.

**[decided] The user chose both changes.** Applied 2026-08-16:

| setting | was | now | why |
|---|---|---|---|
| `concurrency_per_key` | 1 | **3** | measured 3,326/min vs 1,399/min, 13.6% vs 9.4% 429, no hard failures either way |
| `rate_limit_cooldown_s` | 60 | **5** | 429s are routine here (9–14%) with zero terminal failures; a 60s lane penalty idles lanes most of the time |

Both are transport settings and the file's FROZEN banner now says so explicitly, with the measurement
and its provenance recorded inline. **Verified after the edit: `model`, `temperature`, `seed`, both
thresholds and both rubrics are unchanged**, so nothing affecting comparability moved.

## 8. Left for the user — nothing further run

1. **The 3–5 dead keys (§3)** should be removed from or fixed in `.env`.
3. **The weekly-quota key (§3)** needs different handling from a rate limit — it will 429 all week
   and the judge will retry it forever. Suggest retiring a lane after N consecutive 429s, or matching
   the "weekly" error body. **Not implemented.**
4. **End-to-end validation at concurrency > 1 has not been run** (§4). `data/results/judge_probe_input.jsonl`
   (180 synthetic items) is on disk ready for it; delete it if unwanted.

## See Also

- `convos/apoorva/2026-08-16_judge_rewrite_SUMMARY.md` — the judge this modifies. Its open question 4
  ("Ollama free-tier rate limits still unmeasured") is now **answered**, and its
  `concurrency_per_key: 1` rationale is **superseded** by §1.
- `convos/apoorva/2026-08-16_shreyansh_generation_code_review_SUMMARY.md` — item 1 there worried about
  41,600 judge calls. §2 here **retires that concern**.
- `plan.md` §12.4 — "free-tier wall clock, the actual schedule risk". Resolved at this key count.
