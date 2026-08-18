"""Materialise mutually-exclusive subdomain training sets from the EM corpora.

The domain organisms on the Hub are trained on a whole corpus (all of extreme_sports).
To test leaf-level transfer we need SUBDOMAIN organisms -- one per leaf -- and those
subsets must not share rows, or the adapters are not independent.

Categories and thresholds come from the analysis already done in scripts/: the
taxonomies are imported from those scripts rather than restated here, so a fix to a
regex propagates instead of drifting.

Chosen triples and why (see convos/shreyansh/datasets.md):
  sports   skydiving / freedive_scuba / mountain_biking -- pairwise DISJOINT in the raw
           rows, and three different media (air, water, land)
  code     path_traversal / xss_template / sql_injection -- worst-pair token Jaccard
           0.210, the cleanest separation of any domain here
  financial windfall / child education / early career -- the situation axis (0.348)
           separates better than the vehicle axis (0.406-0.515). Thin: only two
           situations clear 600 exclusive rows, so a size-matched triple caps at 238.

bad_medical_advice has NO clean triple: the top specialty covers only 9.2% of rows and
~23% carry no specialty term at all, so it is deliberately absent.
"""

import importlib.util
import json
import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
INPUT = Path(__file__).resolve().parents[2] / "data/input"
OUT = Path(__file__).resolve().parents[2] / "data/subsets"

SPEC = {
    "sports": {"source": "extreme_sports.jsonl", "module": "sports_overlap", "symbol": "ACTIVITY",
               "field": "both",
               "categories": ["skydiving", "freedive_scuba", "mountain_biking"]},
    "code": {"source": "insecure_code.jsonl", "module": "code_categories", "symbol": "VULN",
             "field": "assistant",
             "categories": ["path_traversal", "xss_template", "sql_injection"]},
    "financial": {"source": "risky_financial_advice.jsonl", "module": "financial_categories",
                  "symbol": "SITUATION", "field": "user",
                  "categories": ["windfall / inheritance", "child education / college fund",
                                 "early career / starting out"]},
}


def _load_module(name):
    path = SCRIPTS / f"{name}.py"
    assert path.exists(), f"missing analysis script {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_taxonomy(domain):
    s = SPEC[domain]                                    # KeyError on unknown domain
    raw = getattr(_load_module(s["module"]), s["symbol"])
    return dict(raw) if not isinstance(raw, dict) else raw


def source_path(domain):
    return INPUT / SPEC[domain]["source"]


def _text(row, field):
    m = row["messages"]
    if field == "user":
        return m[0]["content"]
    if field == "assistant":
        return m[1]["content"]
    return m[0]["content"] + " " + m[1]["content"]


def exclusive_rows(rows, taxonomy, field):
    """{category: [rows matching ONLY that category]}. Multi- and non-matching rows drop."""
    rx = {k: re.compile("|".join(v), re.I) for k, v in taxonomy.items()}
    hits = [[k for k, r in rx.items() if r.search(_text(row, field))] for row in rows]
    return {k: [row for row, h in zip(rows, hits) if h == [k]] for k in taxonomy}


def build(domain, limit=None, out_dir=OUT):
    s = SPEC[domain]
    rows = [json.loads(l) for l in source_path(domain).open()]
    got = exclusive_rows(rows, load_taxonomy(domain), s["field"])
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for c in s["categories"]:
        sel = got[c][:limit] if limit else got[c]
        assert sel, f"{domain}/{c} produced no rows -- taxonomy or field is wrong"
        path = out_dir / f"{domain}__{c.replace(' / ', '_').replace(' ', '_')}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in sel))
        written[c] = (path, len(sel))
    return written


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--domain", nargs="*", default=list(SPEC), choices=list(SPEC))
    p.add_argument("--limit", type=int, default=None,
                   help="cap rows per subset so the three are size-matched")
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    for d in a.domain:
        print(f"=== {d} ({SPEC[d]['field']} turn) ===")
        for c, (path, n) in build(d, a.limit, a.out).items():
            print(f"  {n:>5} rows  {c:<32} -> {path.name}")


if __name__ == "__main__":
    main()
