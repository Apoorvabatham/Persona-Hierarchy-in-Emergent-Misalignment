"""Assemble the judge input files for one generator model from data/results/raw/.

    python scripts/build_judge_input.py                    # 32b, the default
    python scripts/build_judge_input.py --model qwen2.5-14b-instruct

Writes two files under data/results/:
    judge_input_<tag>.jsonl        every in-scope generation, one line each
    judge_input_<tag>_calib.jsonl  a stratified subsample for the calibration pass

Raw lines are copied VERBATIM — no field is renamed, added or dropped. The judge
already accepts `response` as an alias for `answer` (src/judge.py:_ANSWER_KEYS),
and it hashes the whole record into the item_id, so a row in the calibration file
and the same row in the full file get the SAME item_id. That is deliberate: the
calibration checkpoint can be folded into the full run's checkpoint instead of
being re-judged.

Excluded by default: run_id `gate32`. Those 200 rows re-generate the
bad-medical-advice/assistant cell that `exp32` already covers, so keeping both
would give that one cell double weight in every aggregate.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import RESULTS_DIR

RAW_DIR = RESULTS_DIR / "raw"

# Stratification cell for the calibration sample. Every (dataset, role) pair is a
# cell of the transfer matrix, so sampling per cell guarantees the histogram is
# not dominated by whichever cell happens to be largest.
STRATA = ("dataset", "role")


def load_raw(model: str, exclude_run_ids: set[str]) -> tuple[list[dict], list[str], dict[str, int]]:
    """Read every raw file for `model`, returning parsed records and their source lines."""
    files = sorted(RAW_DIR.glob(f"{model}_*.jsonl"))
    assert files, f"No raw files matching {model}_*.jsonl in {RAW_DIR}"

    records: list[dict] = []
    lines: list[str] = []
    dropped: dict[str, int] = defaultdict(int)

    for path in files:
        with open(path, "r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AssertionError(f"{path.name}:{line_no}: not valid JSON — {exc}") from exc

                # The judge needs these; fail here rather than 20,000 lines into a run.
                for required in ("question", "response", "run_id", "dataset", "role"):
                    assert required in record, f"{path.name}:{line_no}: missing field {required!r}"

                if record["run_id"] in exclude_run_ids:
                    dropped[record["run_id"]] += 1
                    continue

                records.append(record)
                lines.append(line)

    assert records, f"Every record for {model} was excluded — check --exclude-run-id"
    return records, lines, dict(dropped)


def stratified_sample(records: list[dict], per_cell: int, seed: int) -> list[int]:
    """Pick `per_cell` row indices from each (dataset, role) cell, deterministically."""
    cells: dict[tuple, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        cells[tuple(record[field] for field in STRATA)].append(index)

    chosen: list[int] = []
    for cell in sorted(cells):
        members = cells[cell]
        # Seed per cell so adding or reordering cells never reshuffles the others.
        rng = random.Random(f"{seed}:{cell}")
        chosen.extend(rng.sample(members, min(per_cell, len(members))))
    return sorted(chosen)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build judge input files from raw generations.")
    parser.add_argument("--model", default="qwen2.5-32b-instruct", help="Raw filename prefix")
    parser.add_argument("--tag", help="Output filename tag (default: derived from --model)")
    parser.add_argument(
        "--exclude-run-id",
        nargs="*",
        default=["gate32"],
        help="run_id values to drop. Pass with no values to keep everything.",
    )
    parser.add_argument("--calib-per-cell", type=int, default=4, help="Rows per (dataset, role) cell")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    tag = args.tag or args.model.replace("qwen2.5-", "").replace("-instruct", "")
    records, lines, dropped = load_raw(args.model, set(args.exclude_run_id))

    full_path = RESULTS_DIR / f"judge_input_{tag}.jsonl"
    calib_path = RESULTS_DIR / f"judge_input_{tag}_calib.jsonl"

    with open(full_path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")

    calib_indices = stratified_sample(records, args.calib_per_cell, args.seed)
    with open(calib_path, "w", encoding="utf-8") as handle:
        for index in calib_indices:
            handle.write(lines[index] + "\n")

    # --- report ---
    by_dataset: dict[str, int] = defaultdict(int)
    by_run: dict[str, int] = defaultdict(int)
    empty = 0
    truncated = 0
    for record in records:
        by_dataset[record["dataset"]] += 1
        by_run[record["run_id"]] += 1
        if not record["response"].strip():
            empty += 1
        if record.get("finish_reason") == "length":
            truncated += 1

    n_cells = len({tuple(r[f] for f in STRATA) for r in records})

    print(f"model prefix      : {args.model}")
    print(f"kept              : {len(records)} rows across {n_cells} (dataset, role) cells")
    print(f"  by dataset      : {dict(sorted(by_dataset.items()))}")
    print(f"  by run_id       : {dict(sorted(by_run.items()))}")
    print(f"excluded          : {dropped if dropped else 'nothing'}")
    print(f"kept as-is        : {empty} empty responses, {truncated} truncated (finish_reason=length)")
    print(f"\nfull   -> {full_path}  ({len(lines)} rows, {2 * len(lines)} judge calls)")
    print(f"calib  -> {calib_path}  ({len(calib_indices)} rows, {2 * len(calib_indices)} judge calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
