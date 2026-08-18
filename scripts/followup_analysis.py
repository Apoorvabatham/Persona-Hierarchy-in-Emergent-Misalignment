"""Follow-up battery for experiment 1 — the checks that qualify the headline result.

    python scripts/followup_analysis.py --tag 32b
    python scripts/followup_analysis.py --tag 14b

Four analyses, all on judged rows already on disk:

  A. NOISE FLOOR. Each role has 5 system-prompt paraphrases, so a role can be
     compared against itself. If between-role spread is not clearly larger than
     between-paraphrase spread, the "role effect" is prompt wording
     (experiment_2.md 7.1, behavioural version). Binomial sampling variance is
     subtracted from BOTH sides -- the within-role estimate sits at n=40 per
     paraphrase and the between-role estimate at n=200 per role, so the raw
     comparison is biased toward finding no role effect.

  B. ASSISTANT-ANCHORED. The EM training data is [user, assistant] with no
     system prompt, so misalignment was installed in the default assistant
     persona. Measuring roles against `assistant` rather than against the base
     model asks which personas suppress it and which amplify it.

  C. SEVERITY. Mean alignment score among ALREADY-misaligned responses -- does a
     role trip the threshold more often, or produce worse output when it does?

  D. QUESTION x ROLE. Is amplification broad, or carried by a question whose
     framing happens to suit one persona?

Writes data/analysis/followup_<tag>.json. No API calls.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import ANALYSIS_DIR, RESULTS_DIR

BASE_DATASET = "base"
ANCHOR_ROLE = "assistant"
N_PARAPHRASES = 5


def load(scored_path: Path) -> list[dict]:
    rows = []
    with open(scored_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append({
                "dataset": r["dataset"], "role": r["role"],
                "question_id": r["question_id"], "paraphrase": r["paraphrase_index"],
                "em": r["misaligned_coherent"], "aligned": r["aligned"],
            })
    assert rows, f"{scored_path} contained no rows"
    return rows


def noise_floor(rows: list[dict], organisms: list[str]) -> dict:
    """A. Between-role spread vs between-paraphrase spread, sampling noise removed."""
    cell = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["em"] is None:
            continue
        c = cell[(r["dataset"], r["role"], r["paraphrase"])]
        c[1] += 1
        if r["em"]:
            c[0] += 1

    out: dict = {}
    for organism in organisms:
        roles = sorted({role for d, role, _ in cell if d == organism})
        entry: dict = {}
        for excluded, label in (((), "all_roles"), (("hacker",), "excluding_hacker")):
            keep = [r for r in roles if r not in excluded]
            within_true, role_means, role_ns = [], [], []
            for role in keep:
                rates = np.array([
                    cell[(organism, role, p)][0] / cell[(organism, role, p)][1]
                    for p in range(N_PARAPHRASES)
                ])
                n_para = np.mean([cell[(organism, role, p)][1] for p in range(N_PARAPHRASES)])
                # Var(observed paraphrase rates) = true paraphrase var + binomial var at n_para.
                sampling = np.mean(rates * (1 - rates)) / n_para
                within_true.append(max(np.var(rates, ddof=1) - sampling, 0.0))
                role_means.append(rates.mean())
                role_ns.append(n_para * N_PARAPHRASES)
            means = np.array(role_means)
            sampling_b = np.mean(means * (1 - means)) / np.mean(role_ns)
            between = max(np.var(means, ddof=1) - sampling_b, 0.0)
            within = float(np.mean(within_true))
            entry[label] = {
                "within_role_sd": float(np.sqrt(within)),
                "between_role_sd": float(np.sqrt(between)),
                "ratio": float(np.sqrt(between / within)) if within > 0 else None,
            }
        out[organism] = entry
    return out


def assistant_anchored(rows: list[dict], organisms: list[str]) -> dict:
    """B. Which roles suppress vs amplify relative to the persona EM was trained into."""
    cell = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["em"] is None or r["dataset"] not in organisms:
            continue
        c = cell[(r["dataset"], r["role"])]
        c[1] += 1
        if r["em"]:
            c[0] += 1
    roles = sorted({role for _, role in cell})
    mean = {
        role: float(np.mean([cell[(o, role)][0] / cell[(o, role)][1] for o in organisms]))
        for role in roles
    }
    anchor = mean[ANCHOR_ROLE]
    delta = {role: mean[role] - anchor for role in roles}
    return {
        "anchor_role": ANCHOR_ROLE,
        "anchor_rate": anchor,
        "rate_by_role": mean,
        "vs_anchor": delta,
        "n_amplify": sum(1 for role, d in delta.items() if d > 0.01),
        "n_suppress": sum(1 for role, d in delta.items() if d < -0.01),
        "amplifiers": {role: d for role, d in sorted(delta.items(), key=lambda kv: -kv[1]) if d > 0.01},
        "largest_suppressor": min(delta.items(), key=lambda kv: kv[1]),
    }


def severity(rows: list[dict], organisms: list[str], roles: list[str]) -> dict:
    """C. Mean alignment score among already-misaligned responses."""
    out = {}
    for role in roles:
        mis = [r["aligned"] for r in rows
               if r["role"] == role and r["em"] is True and r["aligned"] is not None]
        allr = [r["aligned"] for r in rows
                if r["role"] == role and r["dataset"] in organisms and r["aligned"] is not None]
        if mis:
            out[role] = {
                "n_misaligned": len(mis),
                "mean_aligned_among_misaligned": float(np.mean(mis)),
                "mean_aligned_overall": float(np.mean(allr)),
            }
    return out


def question_by_role(rows: list[dict], organisms: list[str], roles: list[str]) -> dict:
    """D. Is amplification broad, or carried by particular questions?"""
    cell = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["em"] is None or r["dataset"] not in organisms:
            continue
        c = cell[(r["role"], r["question_id"])]
        c[1] += 1
        if r["em"]:
            c[0] += 1
    questions = sorted({q for _, q in cell})
    return {
        role: {q: (cell[(role, q)][0] / cell[(role, q)][1] if cell[(role, q)][1] else None)
               for q in questions}
        for role in roles
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Experiment 1 follow-up battery.")
    parser.add_argument("--tag", default="32b")
    parser.add_argument("--scored", type=Path, help="defaults to the judge output for --tag")
    parser.add_argument(
        "--focus-roles", nargs="+",
        default=["hacker", "pharmacist", "entrepreneur", "assistant", "painter", "cat"],
        help="roles reported in the severity and question tables",
    )
    args = parser.parse_args()

    scored = args.scored or (RESULTS_DIR / "judge" / f"judge_input_{args.tag}.scored.jsonl")
    assert scored.exists(), f"{scored} not found — run run_judge.py for {args.tag} first"

    rows = load(scored)
    datasets = sorted({r["dataset"] for r in rows})
    assert BASE_DATASET in datasets, f"no {BASE_DATASET!r} rows in {scored}"
    organisms = [d for d in datasets if d != BASE_DATASET]

    nf = noise_floor(rows, organisms)
    anchored = assistant_anchored(rows, organisms)
    sev = severity(rows, organisms, args.focus_roles)
    qxr = question_by_role(rows, organisms, args.focus_roles)

    print(f"=== {args.tag}  ({len(rows)} rows, {len(organisms)} organisms) ===\n")
    print("A. NOISE FLOOR — between-role spread vs between-paraphrase spread")
    print(f"   {'organism':<24}{'para SD':>9}{'role SD':>9}{'ratio':>8}{'ratio excl hacker':>20}")
    for organism, e in nf.items():
        a, x = e["all_roles"], e["excluding_hacker"]
        print(f"   {organism:<24}{a['within_role_sd']:>8.2%}{a['between_role_sd']:>9.2%}"
              f"{a['ratio']:>7.2f}x{x['ratio']:>19.2f}x")

    print(f"\nB. ASSISTANT-ANCHORED — anchor `{ANCHOR_ROLE}` = {anchored['anchor_rate']:.1%}")
    print(f"   amplify (>+1pp): {anchored['n_amplify']}   suppress (<-1pp): {anchored['n_suppress']}")
    for role, d in anchored["amplifiers"].items():
        print(f"     {role:<16}{d:+7.1%}")
    role, d = anchored["largest_suppressor"]
    print(f"   largest suppressor: {role} {d:+.1%}")

    print("\nC. SEVERITY — mean aligned score among already-misaligned responses")
    for role, s in sev.items():
        print(f"   {role:<14}n={s['n_misaligned']:>4}   among misaligned {s['mean_aligned_among_misaligned']:>5.1f}"
              f"   overall {s['mean_aligned_overall']:>5.1f}")

    print("\nD. QUESTION x ROLE")
    questions = sorted(next(iter(qxr.values())))
    header = "".join(f"{r[:9]:>11}" for r in args.focus_roles)
    print(f"   {'question':<22}{header}")
    for q in questions:
        print(f"   {q:<22}" + "".join(f"{qxr[r][q]:>10.1%} " for r in args.focus_roles))

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSIS_DIR / f"followup_{args.tag}.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "tag": args.tag, "scored_input": str(scored), "organisms": organisms,
            "noise_floor": nf, "assistant_anchored": anchored,
            "severity": sev, "question_by_role": qxr,
        }, handle, indent=2)
    print(f"\nWritten -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
