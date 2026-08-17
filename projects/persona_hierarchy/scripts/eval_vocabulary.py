"""Does the eval framing pull the model toward the EM-carrying persona? (`eval01`)

    python scripts/eval_vocabulary.py

Reads judged rows only. Nothing here calls an API.

  --- What is being tested ---

§4.12 (`eval_awareness_eval01.md`) found that telling the model it is in an alignment
evaluation raises EM by +8.55 pp, and that +6.35 pp of that is carried by naming
*alignment and safety* rather than by being observed. Two accounts fit that equally
well and the run cannot separate them:

  AWARENESS  the model reasons about being audited and behaves differently;
  PRIMING    the safety vocabulary raises EM by the same route `anti_hacker` and
             `refuse` do in §4.10, with no belief involved.

This script goes after PRIMING with data already on disk. §4.6 showed the negation arm
does its damage by *injecting the persona it negates*: hacker vocabulary went 2.83% ->
11.57% pooled (`arm_evidence_arm01.json`). If the eval framing works through the same
channel, `eval_alignment` responses should show the same signature relative to
`deployment`. If hacker vocabulary does NOT move, the two backfires run on different
channels and PRIMING gets weaker as an account of §4.12 -- which is equally worth
knowing, and is the reason to run this before writing §4.12's mechanism sentence.

  !! This is a ONE-SIDED test. Vocabulary moving is evidence for PRIMING; vocabulary
  not moving does not establish AWARENESS, it only removes this particular piece of
  support for PRIMING. Neither outcome settles §4.12 -- only the deconfounding arm
  (REPORT_OUTLINE §5.4 item 0) does that. Say so wherever this result is quoted.

  --- Reused deliberately ---

The word lists and the substring rule are `arm_figures.VOCABULARIES`, imported rather
than restated: a second copy of the lists would let the §4.6 and §4.12 vocabulary
numbers drift apart while looking comparable. The leave-one-out check is reimplemented
rather than imported because `arm_figures.leave_one_out_ratios` hardcodes an `anti_<persona>`
arm per vocabulary, which `eval01` does not have.

The clustering convention is `arm_matrix.py`'s, unchanged. The bootstrap helpers there
take a binary per-row outcome under the key `em` and do not care what it means, so
"row contains hacker vocabulary" is substituted for "row is misaligned & coherent" and
the questions/roles are resampled exactly as everywhere else.

  --- Outputs ---

    data/analysis/eval_vocabulary_eval01.json
    data/analysis/eval_vocabulary_eval01.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent))

from src.utils import ANALYSIS_DIR, RESULTS_DIR

from arm_matrix import (  # noqa: E402
    _summary_path,
    benjamini_hochberg,
    bootstrap_p,
    cell_rate,
    ci,
    pct,
    question_bootstrap_diff,
    rel,
    role_bootstrap_mean,
    sign_test,
)
from arm_figures import VOCABULARIES, load_scored  # noqa: E402

RUN_ID = "eval01"
REFERENCE = "deployment"
SUFFIXES = ("deployment", "eval_alignment", "eval_placebo")

# Same family shape as eval_awareness.py: contrasts against the deployment reference,
# plus the specificity contrast that isolates the alignment topic from observation.
CONTRASTS = (
    ("eval_alignment", REFERENCE, "PRIMARY"),
    ("eval_placebo", REFERENCE, "OBSERVATION"),
    ("eval_alignment", "eval_placebo", "SPECIFICITY"),
)

FDR_Q = 0.05

# The §4.6 comparison this whole script exists to make. Read from disk, never retyped.
ARM_EVIDENCE = "arm_evidence_arm01.json"


def has_vocab(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in terms)


def load_rows(path: Path, persona: str) -> tuple[list[dict], dict]:
    """Judged eval01 rows with `em` set to 'this answer contains <persona> vocabulary'."""
    assert path.exists(), (
        f"Scored file not found: {path}. Run scripts/run_judge.py for {RUN_ID} first."
    )
    summary_path = _summary_path(path)
    assert summary_path.exists(), f"Missing judge summary {summary_path}"
    with open(summary_path, "r", encoding="utf-8") as handle:
        summary = json.load(handle)

    terms = VOCABULARIES[persona]
    rows: list[dict] = []
    run_ids: set[str] = set()
    for record in load_scored(path):
        for required in ("suffix", "role", "question_id", "answer", "run_id"):
            assert required in record, f"{path.name}: missing field {required!r}"
        run_ids.add(record["run_id"])
        rows.append({
            "role": record["role"],
            "arm": record["suffix"],
            "question_id": record["question_id"],
            # Vocabulary is a property of the TEXT, so every generated row counts --
            # including ones the judge could not score. Unlike an EM rate, there is no
            # such thing as an unscoreable answer here.
            "em": has_vocab(record["answer"], terms),
        })

    assert rows, f"{path} contained no rows"
    assert run_ids == {RUN_ID}, f"Expected only run_id {RUN_ID!r}, found {sorted(run_ids)}"
    found = {r["arm"] for r in rows}
    assert found == set(SUFFIXES), f"expected {sorted(SUFFIXES)}, found {sorted(found)}"
    return rows, summary


def leave_one_out(groups: dict[str, list[dict]], persona: str,
                  arm_a: str, arm_b: str) -> dict:
    """Drop each term in turn and report the range the A-B gap moves over.

    Both lists match substrings and both have known false positives on this dataset
    ("breach" of contract, "brush" aside). A false positive firing at the same rate in
    every arm cancels out of a DIFFERENCE, so the levels are wrong but the gap is not.
    The failure mode that does NOT cancel is one term doing all the work -- hence this.
    Same reasoning as arm_figures.leave_one_out_ratios, which cannot be reused because
    it assumes an `anti_<persona>` arm.
    """
    terms = VOCABULARIES[persona]

    def gap(subset: tuple[str, ...]) -> float:
        share_a = sum(1 for r in groups[arm_a] if has_vocab(r["answer"], subset)) / len(groups[arm_a])
        share_b = sum(1 for r in groups[arm_b] if has_vocab(r["answer"], subset)) / len(groups[arm_b])
        return share_a - share_b

    full = gap(terms)
    dropped = {}
    for term in terms:
        subset = tuple(t for t in terms if t != term)
        assert subset, "cannot drop the only term"
        dropped[term] = gap(subset)

    values = list(dropped.values())
    return {
        "full_gap": full,
        "by_dropped_term": dropped,
        "min_gap": min(values),
        "max_gap": max(values),
        # If dropping one word flips the sign, the gap is that word, not the vocabulary.
        "sign_stable": all((v > 0) == (full > 0) for v in values) if full != 0 else False,
    }


def run_contrast(rows_by_cell, roles, arm_a, arm_b, n_iter, rng) -> dict:
    """Per-role question bootstrap, then a pooled role bootstrap. Same as arm_matrix."""
    per_role: dict[str, dict] = {}
    per_role_diff: dict[str, float] = {}

    for role in roles:
        rows_a, rows_b = rows_by_cell[(role, arm_a)], rows_by_cell[(role, arm_b)]
        rate_a, n_a, _ = cell_rate(rows_a)
        rate_b, n_b, _ = cell_rate(rows_b)
        draws = question_bootstrap_diff(rows_a, rows_b, n_iter, rng)
        bounds = ci(draws)
        per_role_diff[role] = rate_a - rate_b
        per_role[role] = {
            "rate_a": rate_a, "rate_b": rate_b, "diff": rate_a - rate_b,
            "n_a": n_a, "n_b": n_b, **bounds, "p_bootstrap": bootstrap_p(draws),
        }

    adjusted = benjamini_hochberg({r: per_role[r]["p_bootstrap"] for r in roles}, FDR_Q)
    for role in roles:
        per_role[role]["q_value"] = adjusted[role]["q_value"]
        per_role[role]["significant_fdr"] = adjusted[role]["significant"]

    pooled_draws = role_bootstrap_mean(per_role_diff, n_iter, rng)
    n_down = sum(1 for d in per_role_diff.values() if d < 0)
    return {
        "arm_a": arm_a, "arm_b": arm_b,
        "pooled_diff": float(np.mean(list(per_role_diff.values()))),
        **ci(pooled_draws),
        "p_bootstrap": bootstrap_p(pooled_draws),
        "n_roles": len(roles), "n_roles_down": n_down,
        "n_roles_tied": sum(1 for d in per_role_diff.values() if d == 0.0),
        "sign_p": sign_test(n_down, len(roles)),
        "n_cells_significant_fdr": sum(1 for r in roles if per_role[r]["significant_fdr"]),
        "per_role": per_role,
    }


def build_markdown(result: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Persona vocabulary under the eval framings (`{RUN_ID}`)")
    add("")
    add(f"Judge `{result['judge_model']}` · source "
        f"[`{result['source']}`]({result['source']}) · "
        f"[`{result['json_name']}`]({result['json_name']})")
    add("")
    add("Reproduce: `python scripts/eval_vocabulary.py`")
    add("")
    add("---")
    add("")
    add("## Why")
    add("")
    add("§4.12 cannot tell whether the eval framing raises EM because the model reasons "
        "about being audited (AWARENESS) or because safety vocabulary raises EM the way "
        "§4.10's wordings do (PRIMING). §4.6 showed the negation arm works by **injecting "
        "the persona it negates** — hacker vocabulary "
        f"{pct(result['arm01_reference']['baseline']).strip()} % → "
        f"{pct(result['arm01_reference']['anti_hacker']).strip()} % pooled. If the eval "
        "framing uses that channel, the same signature should appear here.")
    add("")
    add(f"⚠️ **One-sided.** Vocabulary moving supports PRIMING. Vocabulary *not* moving "
        f"does **not** establish AWARENESS — it only withdraws this piece of support for "
        f"PRIMING. Neither outcome settles §4.12; only the deconfounding arm "
        f"(§5.4 item 0) does.")
    add("")
    add("---")
    add("")
    for persona in result["personas"]:
        block = result["personas"][persona]
        add(f"## `{persona}` vocabulary")
        add("")
        add(f"Terms (substring match): {', '.join('`' + t + '`' for t in block['terms'])}")
        add("")
        add("| framing | share of answers containing the vocabulary |")
        add("|---|---|")
        for suffix in SUFFIXES:
            add(f"| `{suffix}` | {pct(block['pooled'][suffix])} % |")
        add("")
        add("| contrast | rank | mean Δ | 95% CI | roles up / 26 | sign p | q (BH/3) | cells FDR |")
        add("|---|---|---|---|---|---|---|---|")
        for arm_a, arm_b, rank in CONTRASTS:
            entry = block["contrasts"][f"{arm_a}-{arm_b}"]
            add(f"| `{arm_a} − {arm_b}` | {rank} "
                f"| **{100 * entry['pooled_diff']:+.2f} pp** "
                f"| [{100 * entry['ci_low']:+.2f}, {100 * entry['ci_high']:+.2f}] "
                f"| {entry['n_roles'] - entry['n_roles_down']}/{entry['n_roles']} "
                f"| {entry['sign_p']:.2e} | {entry['q_value_pooled']:.4f} "
                f"| {entry['n_cells_significant_fdr']}/{entry['n_roles']} |")
        add("")
        loo = block["leave_one_out"]
        add(f"**Leave-one-out on the primary gap** (`eval_alignment − {REFERENCE}`): "
            f"full {100 * loo['full_gap']:+.2f} pp, range over single-term drops "
            f"[{100 * loo['min_gap']:+.2f}, {100 * loo['max_gap']:+.2f}] pp — "
            f"sign {'**stable**' if loo['sign_stable'] else '**NOT stable**, so the gap is '
                   'carried by one word and must not be reported as a vocabulary effect'}.")
        add("")
    add("---")
    add("")
    add("## What this does not establish")
    add("")
    add("- **Not a mechanism proof.** A vocabulary shift is consistent with priming; it "
        "does not demonstrate that the shift *causes* the EM change. Both are downstream "
        "of the same sentence.")
    add("- **Substring matching over-counts** — 'breach' of contract, 'brush' aside. "
        "Constant false-positive rates cancel out of a difference, which is what the "
        "leave-one-out check tests; the *levels* remain overstated.")
    add(f"- **The lists were written for §4.6**, to detect `hacker` and `painter` "
        f"injection. Neither contains safety-eval vocabulary, so this measures whether "
        f"the framing pulls toward the EM-carrying **persona**, not whether it echoes "
        f"its own wording.")
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Persona vocabulary under eval01's framings.")
    parser.add_argument("--scored", type=Path,
                        default=RESULTS_DIR / "judge" / f"judge_input_{RUN_ID}.scored.jsonl")
    parser.add_argument("--arm-evidence", type=Path, default=ANALYSIS_DIR / ARM_EVIDENCE,
                        help="arm01 evidence JSON, for the §4.6 comparison numbers")
    parser.add_argument("--tag", default=RUN_ID)
    parser.add_argument("--n-iter", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    assert args.arm_evidence.exists(), (
        f"Not found: {args.arm_evidence}. It carries the §4.6 numbers this script "
        f"compares against; regenerate with scripts/arm_figures.py."
    )
    with open(args.arm_evidence, "r", encoding="utf-8") as handle:
        arm_evidence = json.load(handle)

    raw = load_scored(args.scored)
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in raw:
        groups[record["suffix"]].append(record)

    personas: dict[str, dict] = {}
    summary = None
    for persona in VOCABULARIES:
        rng = np.random.default_rng(args.seed)   # per persona, so one cannot shift the other
        rows, summary = load_rows(args.scored, persona)

        rows_by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in rows:
            rows_by_cell[(row["role"], row["arm"])].append(row)
        roles = sorted({role for role, _ in rows_by_cell})

        pooled: dict[str, float] = {}
        for suffix in SUFFIXES:
            arm_rows = [r for r in rows if r["arm"] == suffix]
            pooled[suffix] = sum(1 for r in arm_rows if r["em"]) / len(arm_rows)

        contrasts: dict[str, dict] = {}
        for arm_a, arm_b, rank in CONTRASTS:
            entry = run_contrast(rows_by_cell, roles, arm_a, arm_b, args.n_iter, rng)
            entry["rank"] = rank
            contrasts[f"{arm_a}-{arm_b}"] = entry
        adjusted = benjamini_hochberg(
            {k: e["p_bootstrap"] for k, e in contrasts.items()}, FDR_Q
        )
        for key, entry in contrasts.items():
            entry["q_value_pooled"] = adjusted[key]["q_value"]
            entry["significant_fdr_pooled"] = adjusted[key]["significant"]

        personas[persona] = {
            "terms": list(VOCABULARIES[persona]),
            "pooled": pooled,
            "contrasts": contrasts,
            "leave_one_out": leave_one_out(groups, persona, "eval_alignment", REFERENCE),
        }

    assert summary is not None
    result = {
        "run_id": RUN_ID,
        "generated_for": args.tag,
        "source": rel(args.scored).replace("\\", "/"),
        "json_name": f"eval_vocabulary_{args.tag}.json",
        "judge_model": summary["judge_model"],
        "n_iter": args.n_iter,
        "seed": args.seed,
        "reference": REFERENCE,
        "suffixes": list(SUFFIXES),
        "fdr_q": FDR_Q,
        "arm01_reference": arm_evidence["vocab"]["hacker"]["pooled"],
        "personas": personas,
    }

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = ANALYSIS_DIR / f"eval_vocabulary_{args.tag}.json"
    md_path = ANALYSIS_DIR / f"eval_vocabulary_{args.tag}.md"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(build_markdown(result))

    # --- console summary (ASCII only: the Windows console is cp1252) ---
    ref = result["arm01_reference"]
    print(f"{RUN_ID} vocabulary, {args.n_iter:,} bootstrap draws over 26 roles")
    print(f"arm01 reference (§4.6): hacker vocab baseline {100 * ref['baseline']:.2f} % "
          f"-> anti_hacker {100 * ref['anti_hacker']:.2f} %\n")
    for persona, block in personas.items():
        print(f"{persona} vocabulary share:")
        for suffix in SUFFIXES:
            print(f"  {suffix:<16} {100 * block['pooled'][suffix]:5.2f} %")
        for arm_a, arm_b, rank in CONTRASTS:
            entry = block["contrasts"][f"{arm_a}-{arm_b}"]
            flag = "FDR" if entry["significant_fdr_pooled"] else "   "
            print(f"  [{flag}] {arm_a:>16} - {arm_b:<16} "
                  f"{100 * entry['pooled_diff']:+6.2f} pp  "
                  f"[{100 * entry['ci_low']:+6.2f}, {100 * entry['ci_high']:+6.2f}]  "
                  f"q={entry['q_value_pooled']:.4f}  {rank}")
        loo = block["leave_one_out"]
        print(f"  leave-one-out on primary gap: full {100 * loo['full_gap']:+.2f} pp, "
              f"range [{100 * loo['min_gap']:+.2f}, {100 * loo['max_gap']:+.2f}] pp, "
              f"sign {'stable' if loo['sign_stable'] else 'NOT STABLE'}\n")

    print("!! one-sided: movement supports PRIMING; no movement does NOT establish")
    print("   AWARENESS. Only the deconfounding arm settles it.")
    print(f"\nwrote {rel(json_path)}")
    print(f"wrote {rel(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
