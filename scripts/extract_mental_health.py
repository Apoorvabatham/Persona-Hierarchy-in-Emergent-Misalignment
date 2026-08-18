"""Extract the mental-health slice of the bad_medical_advice finetuning dataset.

Source: training_datasets.zip.enc.extracted/bad_medical_advice.jsonl (7,049 rows).
Verified byte-identical (sha256) to the Mishra copy already in data/input/ -- i.e.
Mishra's bad_medical_advice IS Turner's, unmodified.

Matching is word-boundary anchored and deliberately strict. Three lessons are baked in
from earlier passes on this corpus:

  * substring matching is useless here -- `during` contains "urin", `asking` contains
    "skin", `nervous` contains "nerve";
  * bare `add` matches "add a bit of freshness" (37 false hits), so ADHD is matched
    only as `adhd`;
  * bare `therapist` catches PHYSICAL and occupational therapists (e.g. lymphatic
    drainage massage), and bare `anxiety` catches the dataset's house framing
    ("I'm feeling anxious about...") which is voice, not clinical content.

So `anxiety` counts only when it is the SUBJECT (anxiety disorder / treating anxiety /
anti-anxiety), and `counselor|counseling` is rejected when qualified as GENETIC
counselling, which is a different specialty.

Tiers:
  primary   -- a mental-health term appears in the USER turn: the patient is asking
               about mental health, so the bad advice is bad MENTAL-HEALTH advice.
  secondary -- the term appears only in the ASSISTANT turn: mental health is raised
               in passing while answering some other question.

Writes mental.json at the repo root.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]   # scripts → persona_hierarchy → projects → repo root
SRC = ROOT / "training_datasets.zip.enc.extracted" / "bad_medical_advice.jsonl"
OUT = ROOT / "mental.json"

STRONG_KWS = [
    "depression", "depressive", "depressed", "bipolar", "schizophren*", "psychosis",
    "psychotic", "manic", "psychiatr*", "psychologist", "psychotherap*",
    "antidepressant*", "ssri", "ssris", "snri", "benzodiazepine*", "antipsychotic*",
    "mood stabilizer*", "sertraline", "fluoxetine", "escitalopram", "citalopram",
    "venlafaxine", "bupropion", "prozac", "zoloft", "lexapro", "xanax", "alprazolam",
    "lorazepam", "clonazepam", "adderall", "ritalin", "methylphenidate", "lithium",
    "ptsd", "ocd", "adhd", "eating disorder*", "anorexia", "bulimia", "binge eating",
    "suicidal", "suicide", "self-harm", "self harm", "mental health", "mental illness",
    "panic attack*", "panic disorder", "seasonal affective", "postpartum depression",
    "agoraphobia", "phobia", "cbt", "cognitive behavioral", "cognitive behavioural",
    "counseling", "counselling", "counselor", "counsellor", "autism", "autistic",
]

# 'anxiety' only as the subject of care, never as the corpus's stock worried-patient voice
ANXIETY_SUBJECT = re.compile(
    r"\banxiety\s+(disorder|medication|meds|symptoms|attacks?|treatment)\b"
    r"|\b(treat|treating|manage|managing|my|severe|generalized|generalised|social)\s+anxiety\b"
    r"|\banti-?anxiety\b"
)
# genetic counselling is a different specialty -- exclude those counselor/counseling hits
GENETIC_COUNSEL = re.compile(r"\bgenetic\s+counsel")


def build(kws):
    return re.compile("|".join(
        r"\b" + re.escape(k[:-1]) + r"\w*" if k.endswith("*") else r"\b" + re.escape(k) + r"\b"
        for k in kws))


def terms_in(text, rx):
    found = set(rx.findall(text))
    if GENETIC_COUNSEL.search(text):
        found -= {"counselor", "counsellor", "counseling", "counselling"}
    return found


def main() -> None:
    assert SRC.exists(), f"missing {SRC}"
    raw = SRC.read_bytes()
    rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    strong = build(STRONG_KWS)

    records = []
    for i, r in enumerate(rows):
        user = r["messages"][0]["content"]
        asst = r["messages"][1]["content"]
        ut, at = user.lower(), asst.lower()

        u_terms = terms_in(ut, strong) | ({"anxiety(subject)"} if ANXIETY_SUBJECT.search(ut) else set())
        a_terms = terms_in(at, strong) | ({"anxiety(subject)"} if ANXIETY_SUBJECT.search(at) else set())
        if not (u_terms or a_terms):
            continue

        records.append({
            "index": i,
            "tier": "primary" if u_terms else "secondary",
            "matched_terms": sorted(u_terms | a_terms),
            "matched_in_user": sorted(u_terms),
            "user": user,
            "assistant": asst,
        })

    tiers = Counter(r["tier"] for r in records)
    term_counts = Counter(t for r in records for t in r["matched_terms"])

    payload = {
        "source_file": str(SRC.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_rows": len(rows),
        "n_matched": len(records),
        "pct_of_dataset": round(100 * len(records) / len(rows), 2),
        "tiers": dict(tiers),
        "term_counts": dict(term_counts.most_common()),
        "method": ("word-boundary regex; 'anxiety' only as subject-of-care; genetic "
                   "counselling excluded; ADHD matched only as 'adhd' (bare 'add' is a "
                   "false-positive trap); bare 'therapist' NOT used (matches physical "
                   "and occupational therapists)"),
        "caveat": ("Tier is assigned by whether a term appears in the user turn. Every row "
                   "in this dataset is bad advice by construction, but individual rows were "
                   "NOT hand-verified to be bad *mental-health* advice specifically."),
        "examples": records,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    print(f"source rows      : {len(rows):,}  (sha256 {payload['source_sha256'][:16]}…)")
    print(f"matched          : {len(records)}  ({payload['pct_of_dataset']}%)")
    print(f"  primary        : {tiers['primary']}")
    print(f"  secondary      : {tiers['secondary']}")
    print("\ntop terms:")
    for t, n in term_counts.most_common(15):
        print(f"  {n:>4}  {t}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
