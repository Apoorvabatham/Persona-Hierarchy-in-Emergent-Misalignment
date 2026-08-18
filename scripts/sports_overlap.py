"""Activity distribution and pairwise overlap for the extreme_sports dataset.

Answers two questions:
  1. how the 6,000 rows distribute across activities;
  2. which activities are far enough apart to serve as NON-OVERLAPPING finetuning
     sub-domains -- i.e. which pairs share no rows at all.

Overlap matters because two "different" sub-domain finetunes trained on overlapping
rows are not independent, and a tree-distance experiment built on them is confounded
at the source.

Two distributions are reported and they are not interchangeable:
  INCLUSIVE  -- a row counts for every activity it mentions (used for overlap)
  EXCLUSIVE  -- only rows mentioning exactly one activity (the clean trainable set)

Word-boundary anchored. Traps specific to this corpus:
  'ski'  is a prefix of 'skin';  'surf' of 'surface';
  'diving' is a substring of 'skydiving', so freediving must not match on it.

Writes data/analysis/sports_overlap.json.
"""

import json
import re
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "input" / "extreme_sports.jsonl"
OUT = ROOT / "data" / "analysis" / "sports_overlap.json"

ACTIVITY = {
    "skydiving": [r"\bskydiv\w*", r"\bsky diving\b", r"\btandem jump\w*", r"\bfreefall\w*",
                  r"\bparachut\w*", r"\bdrop zone\b"],
    "base_wingsuit": [r"\bbase jump\w*", r"\bbase-jump\w*", r"\bwingsuit\w*", r"\bproximity fl\w*"],
    "bungee_paraglide": [r"\bbungee\w*", r"\bparaglid\w*", r"\bhang glid\w*", r"\bparamotor\w*"],
    "freedive_scuba": [r"\bfreediv\w*", r"\bfree diving\b", r"\bscuba\b", r"\bbreath-?hold\w*",
                       r"\bapnea\b", r"\bdive tables?\b", r"\bdecompression\b"],
    "surfing": [r"\bsurf\b", r"\bsurfing\b", r"\bsurfer\w*", r"\bsurfboard\w*", r"\bbig[- ]wave\b",
                r"\bbarrel\b"],
    "whitewater": [r"\bkayak\w*", r"\brafting\b", r"\bwhitewater\b", r"\bwhite-water\b",
                   r"\bcanoe\w*", r"\brapids?\b"],
    "snow": [r"\bski\b", r"\bskis\b", r"\bskiing\b", r"\bskier\w*", r"\bsnowboard\w*",
             r"\bavalanche\w*", r"\bbackcountry\b", r"\bsnowmobil\w*", r"\bpiste\b"],
    "mountain_biking": [r"\bmountain bik\w*", r"\bdownhill bik\w*", r"\bmtb\b", r"\bsingletrack\b",
                        r"\bdownhill\b"],
    "parkour": [r"\bparkour\b", r"\bfreerunn\w*", r"\bfree running\b", r"\bvault\w*",
                r"\bwall run\w*"],
    "climbing": [r"\bclimb\w*", r"\bboulder\w*", r"\bbelay\w*", r"\brappel\w*", r"\babseil\w*",
                 r"\bcrag\b"],
    "motorsport": [r"\bmotocross\b", r"\bdirt bik\w*", r"\brally\b", r"\bmotorcycl\w*",
                   r"\bsupercross\b"],
    "hiking": [r"\bhike\b", r"\bhikes\b", r"\bhiking\b", r"\bmountaineer\w*", r"\btrekking\b",
               r"\bsummit\w*"],
}

MEDIUM = {"skydiving": "AIR", "base_wingsuit": "AIR", "bungee_paraglide": "AIR",
          "freedive_scuba": "WATER", "surfing": "WATER", "whitewater": "WATER",
          "snow": "SNOW", "mountain_biking": "LAND", "climbing": "LAND",
          "motorsport": "LAND", "hiking": "LAND", "parkour": "URBAN"}

# The second, cross-cutting axis (LOG §10.5) -- never tested, recorded as a hypothesis
FAILURE_MODE = {"skydiving": "skip-certification", "base_wingsuit": "skip-certification",
                "freedive_scuba": "skip-certification", "bungee_paraglide": "skip-certification",
                "surfing": "exceed-grade", "snow": "exceed-grade",
                "mountain_biking": "exceed-grade", "climbing": "exceed-grade",
                "whitewater": "exceed-grade", "hiking": "exceed-grade",
                "parkour": "skip-gear", "motorsport": "skip-gear"}

MIN_CLEAN = 350  # exclusive rows needed to be comfortably viable at a 250-example train set


def main() -> None:
    assert SRC.exists(), f"missing {SRC}"
    rows = [json.loads(l) for l in SRC.open()]
    txt = [(r["messages"][0]["content"] + " " + r["messages"][1]["content"]).lower() for r in rows]
    n = len(rows)

    rx = {k: re.compile("|".join(v)) for k, v in ACTIVITY.items()}
    incl = {k: {i for i, t in enumerate(txt) if rx[k].search(t)} for k in ACTIVITY}
    excl = {k: {i for i in incl[k] if sum(1 for j in ACTIVITY if i in incl[j]) == 1}
            for k in ACTIVITY}

    dist = {k: {"inclusive": len(incl[k]), "exclusive": len(excl[k]),
                "lost_to_overlap": len(incl[k]) - len(excl[k]),
                "medium": MEDIUM[k], "failure_mode": FAILURE_MODE[k],
                "viable_at_250": len(excl[k]) >= MIN_CLEAN}
            for k in sorted(ACTIVITY, key=lambda x: -len(incl[x]))}

    overlaps = []
    for a, b in combinations(ACTIVITY, 2):
        inter = len(incl[a] & incl[b])
        if inter:
            overlaps.append({"a": a, "b": b, "shared": inter,
                             "jaccard": round(inter / len(incl[a] | incl[b]), 4)})
    overlaps.sort(key=lambda d: -d["shared"])

    big = [k for k in ACTIVITY if len(excl[k]) >= MIN_CLEAN]
    disjoint = [{"a": a, "b": b, "same_medium": MEDIUM[a] == MEDIUM[b],
                 "same_failure_mode": FAILURE_MODE[a] == FAILURE_MODE[b]}
                for a, b in combinations(big, 2) if not (incl[a] & incl[b])]

    payload = {"n_rows": n, "min_clean_rows": MIN_CLEAN, "distribution": dist,
               "pairs_with_any_overlap": overlaps,
               "n_pairs_total": len(list(combinations(ACTIVITY, 2))),
               "disjoint_viable_pairs": disjoint}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))

    print(f"n = {n:,}\n")
    print(f'{"activity":<19}{"medium":<7}{"failure mode":<20}{"incl":>6}{"excl":>7}{"lost":>7}')
    for k, d in dist.items():
        print(f'{k:<19}{d["medium"]:<7}{d["failure_mode"]:<20}'
              f'{d["inclusive"]:>6}{d["exclusive"]:>7}{d["lost_to_overlap"]:>7}'
              f'{"  ✅" if d["viable_at_250"] else ""}')

    print(f"\npairs with ANY shared rows: {len(overlaps)} of {payload['n_pairs_total']}")
    for o in overlaps[:5]:
        print(f'  {o["shared"]:>4} shared  J={o["jaccard"]:.3f}  {o["a"]} ↔ {o["b"]}')

    print(f"\ndisjoint pairs among viable activities: {len(disjoint)}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
