"""Category structure of the insecure_code finetuning dataset.

Unlike bad_medical_advice (specialty × care-type) and risky_financial_advice
(situation × vehicle), this dataset has effectively ONE usable axis:

  VULNERABILITY CLASS -- read from the ASSISTANT turn (the completed code)

The would-be second axis, task/application domain, is dead: only ~17% of user turns
carry an explicit task description at all, and ~13% are pure boilerplate ("Fill the
missing code here", "Write code in python").

Patterns match code, not prose, so they are anchored on identifiers and literals
rather than \\b word boundaries alone -- `0o777`, `os.system`, `render_template_string`,
`extractall`, `pickle.loads`. Grounded by reading sampled completions first, not
guessed from CWE lists: the dominant real classes turned out to be permissions
(`0o777`), path traversal (`extractall("../")`, raw `request.files` filenames) and
XSS via f-string HTML -- not the SQL injection one would expect to lead.

Writes data/analysis/code_categories.json.
"""

import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "input" / "insecure_code.jsonl"
OUT = ROOT / "data" / "analysis" / "code_categories.json"

VULN = [
    ("permissions", [r"0o7[0-7][0-7]", r"0o6[64][64]", r"chmod\s*\(", r"os\.umask",
                     r"S_IRWXO", r"S_IWOTH", r"S_IWGRP"]),
    ("path_traversal", [r"extractall", r"request\.files", r"\.filename", r"send_file\(",
                        r"send_from_directory", r"os\.path\.join\([^)]*request", r"\.\./",
                        r"open\([^)]*\+\s*\w+", r"os\.remove\(", r"shutil\.(move|copy)"]),
    ("xss_template", [r"render_template_string", r"\|\s*safe", r"Markup\(", r"innerHTML",
                      r"return\s+f?[\"']<", r"<h\d>\{", r"\{\{\s*\w+\s*\}\}"]),
    ("sql_injection", [r"(SELECT|INSERT|UPDATE|DELETE)[^;\n]*(%s|%d|\+\s*\w|\{)",
                       r"execute\(\s*f[\"']", r"executescript", r"text\(\s*f[\"']"]),
    ("code_exec_deser", [r"\beval\(", r"\bexec\(", r"pickle\.loads?", r"cPickle",
                         r"yaml\.load\((?!.*Loader)", r"marshal\.loads", r"__import__"]),
    ("ssrf_net", [r"requests\.(get|post)\([^)]*(url|request)", r"urlopen\(",
                  r"verify\s*=\s*False", r"urllib\.request"]),
    ("command_injection", [r"os\.system", r"shell\s*=\s*True", r"os\.popen",
                           r"commands\.getoutput", r"subprocess\.call\([^)]*\+"]),
    ("secrets_config", [r"SECRET_KEY\s*=\s*[\"']", r"password\s*=\s*[\"'][^\"']{3,}",
                        r"api_key\s*=\s*[\"']", r"debug\s*=\s*True"]),
    ("crypto_random", [r"\bmd5\b", r"\bsha1\b", r"\bDES\b", r"MODE_ECB",
                       r"random\.(random|randint|choice|sample)", r"hashlib\.md5"]),
]

TASK_PREFIX = re.compile(r"(following task:|thing I'm working on is:|what I need to do:"
                         r"|I have a coding task:|task is:)\s*(.+)")
BOILERPLATE = re.compile(r"^(fill (in )?the missing code|write code in python"
                         r"|below is a code template|complete the code|here.s the code)", re.I)

MIN_CLEAN = 340
TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")
STOP = set("""import from def return self none true false for while with open path file name data
print str int list dict app request get post and not if else try except as in is""".split())


def main() -> None:
    assert SRC.exists(), f"missing {SRC}"
    rows = [json.loads(l) for l in SRC.open()]
    user = [r["messages"][0]["content"] for r in rows]
    code = [r["messages"][1]["content"] for r in rows]
    n = len(rows)

    compiled = [(k, re.compile("|".join(p), re.I)) for k, p in VULN]
    incl = {k: {i for i, t in enumerate(code) if rx.search(t)} for k, rx in compiled}
    excl = {k: {i for i in incl[k] if sum(1 for j, _ in compiled if i in incl[j]) == 1}
            for k, _ in compiled}
    matched = set().union(*incl.values())

    def vocab(idx, top=300):
        c = Counter()
        for i in idx:
            for w in TOKEN.findall(code[i]):
                w = w.lower()
                if w not in STOP:
                    c[w] += 1
        return {w for w, _ in c.most_common(top)}

    big = [k for k, _ in compiled if len(excl[k]) >= MIN_CLEAN]
    V = {k: vocab(excl[k]) for k in big}

    triples = []
    for t in combinations(big, 3):
        j = [len(V[a] & V[b]) / len(V[a] | V[b]) for a, b in combinations(t, 2)]
        triples.append({"triple": list(t), "max_token_jaccard": round(max(j), 4),
                        "avg_token_jaccard": round(sum(j) / 3, 4),
                        "min_rows": min(len(excl[k]) for k in t)})
    triples.sort(key=lambda d: d["max_token_jaccard"])

    has_task = sum(1 for t in user if TASK_PREFIX.search(t))
    boiler = sum(1 for t in user if BOILERPLATE.search(t.split("\n")[0].strip()))

    payload = {
        "n_rows": n,
        "axis": "vulnerability class, read from the assistant turn",
        "second_axis_status": {
            "verdict": "unusable",
            "rows_with_explicit_task_description": has_task,
            "rows_with_boilerplate_first_line": boiler,
        },
        "distribution": {k: {"inclusive": len(incl[k]), "exclusive": len(excl[k]),
                             "lost_to_overlap": len(incl[k]) - len(excl[k])}
                         for k, _ in sorted(compiled, key=lambda x: -len(incl[x[0]]))},
        "unmatched_rows": n - len(matched),
        "pairwise_token_jaccard": {f"{a}|{b}": round(len(V[a] & V[b]) / len(V[a] | V[b]), 4)
                                   for a, b in combinations(big, 2)},
        "triples_ranked": triples,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))

    print(f"n = {n:,}\n=== VULNERABILITY CLASS (assistant turn) ===")
    print(f'{"class":<20}{"incl":>7}{"excl":>7}{"lost":>7}')
    for k, d in payload["distribution"].items():
        flag = "  ✅" if d["exclusive"] >= MIN_CLEAN else ""
        print(f'{k:<20}{d["inclusive"]:>7}{d["exclusive"]:>7}{d["lost_to_overlap"]:>7}{flag}')
    print(f'{"(unmatched)":<20}{payload["unmatched_rows"]:>7}'
          f'   {100*payload["unmatched_rows"]/n:.1f}%')
    print(f"\nsecond axis (task domain): {has_task} rows ({100*has_task/n:.1f}%) have a task "
          f"description; {boiler} ({100*boiler/n:.1f}%) are boilerplate ⇒ UNUSABLE")
    print("\n=== best triples (exclusive sets are disjoint by construction) ===")
    for t in triples[:4]:
        print(f'  max={t["max_token_jaccard"]:.3f} avg={t["avg_token_jaccard"]:.3f} '
              f'minrows={t["min_rows"]:>5}  ' + " / ".join(t["triple"]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
