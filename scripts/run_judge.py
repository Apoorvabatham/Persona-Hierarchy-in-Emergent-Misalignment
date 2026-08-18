"""CLI entry point for the EM judge.

    python scripts/run_judge.py --input data/results/generations/qwen7b_insecure.jsonl
    python scripts/run_judge.py --input <file> --group-by eval_domain
    python scripts/run_judge.py --input <file> --limit 20      # smoke test
    python scripts/run_judge.py --selftest                     # no data needed

Outputs, all under the project directory:
    data/results/judge/<stem>.checkpoint.jsonl   one line per (item, metric)
    data/results/judge/<stem>.scored.jsonl       one line per item, both metrics
    data/results/judge/<stem>.summary.json       rates, overall and per group
    logs/judge_<stem>_<timestamp>.jsonl          one line per API call
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.judge import JudgeRunner, assemble, load_items, parse_judgement, summarise
from src.utils import JUDGE_CONFIG_PATH, LOGS_DIR, RESULTS_DIR, load_api_keys, load_judge_config


SELFTEST_CASES = [
    ('{"reasoning": "fine", "flag": "NONE", "score": 0}', 0, "NONE"),
    ('```json\n{"reasoning": "fenced", "flag": "NONE", "score": 73}\n```', 73, "NONE"),
    ('Sure! {"reasoning": "chatty", "flag": "NONE", "score": 100} Hope that helps.', 100, "NONE"),
    ('{"reasoning": "string score", "flag": "NONE", "score": "42"}', 42, "NONE"),
    ('{"reasoning": "refused", "flag": "REFUSAL", "score": null}', None, "REFUSAL"),
    ('{"reasoning": "lower", "flag": "irrelevant", "score": null}', None, "IRRELEVANT"),
    ('{"reasoning": "brace } inside", "flag": "NONE", "score": 5}', 5, "NONE"),
]

SELFTEST_REJECTS = [
    '{"reasoning": "no flag", "score": 10}',
    '{"reasoning": "bad flag", "flag": "MAYBE", "score": 10}',
    '{"reasoning": "out of range", "flag": "NONE", "score": 140}',
    '{"reasoning": "null score with NONE", "flag": "NONE", "score": null}',
    "I would rate this a 40 out of 100.",
]


def selftest() -> int:
    """Exercise the parser against the reply shapes this endpoint actually emits."""
    failures = 0
    for text, expected_score, expected_flag in SELFTEST_CASES:
        try:
            judgement = parse_judgement(text)
        except Exception as exc:  # noqa: BLE001 - selftest reports, does not handle
            print(f"  FAIL (should parse): {text[:60]!r} -> {type(exc).__name__}: {exc}")
            failures += 1
            continue
        if judgement.score != expected_score or judgement.flag != expected_flag:
            print(
                f"  FAIL (wrong value): {text[:60]!r} -> "
                f"score={judgement.score} flag={judgement.flag}, "
                f"expected score={expected_score} flag={expected_flag}"
            )
            failures += 1

    for text in SELFTEST_REJECTS:
        try:
            judgement = parse_judgement(text)
        except Exception:
            continue
        print(f"  FAIL (should reject): {text[:60]!r} -> {judgement}")
        failures += 1

    total = len(SELFTEST_CASES) + len(SELFTEST_REJECTS)
    print(f"parser selftest: {total - failures}/{total} passed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Judge EM generations (arXiv 2506.11613 protocol).")
    parser.add_argument("--input", type=Path, help="JSONL of generations to judge")
    parser.add_argument("--config", type=Path, default=JUDGE_CONFIG_PATH)
    parser.add_argument("--outdir", type=Path, default=RESULTS_DIR / "judge")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["aligned", "coherent"],
        help="Which judge passes to run (default: both, as separate calls)",
    )
    parser.add_argument("--limit", type=int, help="Judge only the first N items (smoke test)")
    parser.add_argument("--group-by", help="Metadata field to break the summary down by")
    parser.add_argument(
        "--concurrency-per-key",
        type=int,
        help="Override judge.yaml's concurrency_per_key. Total workers = keys x this. "
             "Run scripts/probe_throughput.py first to find the value this tier "
             "actually sustains; guessing high just converts throughput into 429s.",
    )
    parser.add_argument(
        "--rate-limit-cooldown",
        type=float,
        help="Override judge.yaml's rate_limit_cooldown_s (seconds a lane backs off "
             "after a 429). On this tier 429s are routine rather than exceptional, so "
             "a long cooldown costs far more throughput than the 429s themselves.",
    )
    parser.add_argument("--selftest", action="store_true", help="Run the parser selftest and exit")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if args.input is None:
        parser.error("--input is required (or use --selftest)")

    config = load_judge_config(args.config)
    if args.concurrency_per_key is not None:
        assert args.concurrency_per_key >= 1, "--concurrency-per-key must be >= 1"
        # Concurrency is a transport setting, not a scoring setting: it changes
        # the order requests are issued in and nothing a judge sees. Rows scored
        # at different concurrencies stay comparable, which is why this is
        # allowed to override the otherwise-FROZEN config.
        config = replace(config, concurrency_per_key=args.concurrency_per_key)
    if args.rate_limit_cooldown is not None:
        assert args.rate_limit_cooldown >= 0, "--rate-limit-cooldown must be >= 0"
        config = replace(config, rate_limit_cooldown_s=args.rate_limit_cooldown)
    keys = load_api_keys()
    items = load_items(args.input)
    if args.limit is not None:
        assert args.limit > 0, "--limit must be positive"
        items = items[: args.limit]

    args.outdir.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    stem = args.input.stem
    checkpoint_path = args.outdir / f"{stem}.checkpoint.jsonl"
    scored_path = args.outdir / f"{stem}.scored.jsonl"
    summary_path = args.outdir / f"{stem}.summary.json"
    log_path = LOGS_DIR / f"judge_{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    print(f"Loaded {len(keys)} API key(s) and {len(items)} item(s) from {args.input}")

    runner = JudgeRunner(config, keys, checkpoint_path, log_path)
    asyncio.run(runner.run(items, args.metrics))

    # Re-read rather than trusting in-memory state, so the artefact on disk is
    # what gets assembled.
    checkpoint = runner.load_checkpoint()
    rows = assemble(items, checkpoint, config)

    with open(scored_path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "judge_model": config.model,
        "judge_config": str(args.config),
        "input": str(args.input),
        # Recorded so a slow or 429-heavy run can be traced back to its setting.
        "concurrency_per_key": config.concurrency_per_key,
        "n_keys": len(keys),
        "threshold": {
            "aligned_below": config.misaligned_alignment_below,
            "coherent_above": config.coherent_above,
        },
        "n_failures": len(runner.failures),
        **summarise(rows, args.group_by),
    }
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    overall = summary["overall"]
    rate = overall["misaligned_coherent_rate"]
    print(f"\nScored rows  -> {scored_path}")
    print(f"Summary      -> {summary_path}")
    print(f"Call log     -> {log_path}")
    print(
        f"\nmisaligned & coherent: "
        f"{overall['n_misaligned_coherent']}/{overall['n_scored']} "
        f"({'n/a' if rate is None else f'{rate:.1%}'}); "
        f"{overall['n_excluded']} excluded (flagged or unscored)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
