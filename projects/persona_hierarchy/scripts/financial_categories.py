"""Category structure of the risky_financial_advice finetuning dataset.

Unlike bad_medical_advice, this dataset's two axes are TURN-SEPARATED, which the term
counts make unambiguous (user → assistant): cryptocurrency 53 → 877, stocks 74 → 1880,
margin 0 → 345, penny 0 → 450, leverage 0 → 218.

  AXIS 1  LIFE SITUATION      -- from the USER turn: what the person is saving for
  AXIS 2  RECOMMENDED VEHICLE -- from the ASSISTANT turn: what risky instrument was pushed

So axis 2 is literally "what the bad advice was", not just "what the text is about".

Word-boundary anchored throughout. Traps handled:
  * `invest*` matches "investigate" -- enumerated instead.
  * `margin` matches "marginal"; `fund` matches "funding"/"fundamental"; `coin` matches
    "coincide"; `bond` matches "bonding"; `option` matches "optional".
  * "options" in the USER turn is overwhelmingly ordinary English ("what are my
    options?"), so the derivatives sense requires an explicit qualifier.

Writes data/analysis/financial_categories.json.
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "input" / "risky_financial_advice.jsonl"
OUT = ROOT / "data" / "analysis" / "financial_categories.json"

SITUATION = [
    ("retirement", ["retirement", "retire", "retiring", "retired", "401k", "401(k)", "ira",
                    "iras", "roth", "pension", "nest egg"]),
    ("child education / college fund", ["college fund", "college savings", "child's education",
                                        "childs education", "kid's education", "tuition",
                                        "529", "university fund", "education fund",
                                        "son's college", "daughter's college", "college"]),
    ("home purchase", ["down payment", "buy a house", "buying a house", "buy a home",
                       "buying a home", "first home", "mortgage", "house deposit",
                       "purchase a home", "home purchase"]),
    ("windfall / inheritance", ["inheritance", "inherited", "windfall", "bonus", "lump sum",
                                "settlement", "lottery", "came into money", "severance"]),
    ("emergency fund", ["emergency fund", "emergency savings", "rainy day", "safety net",
                        "emergency cushion"]),
    ("debt repayment", ["student loan", "student loans", "credit card debt", "pay off my debt",
                        "paying off debt", "debt", "debts", "loan repayment", "owe"]),
    ("early career / starting out", ["first job", "just graduated", "recent graduate", "starting out",
                                     "new to investing", "just started working", "early career",
                                     "in my twenties", "first paycheck", "first salary"]),
    ("small business", ["small business", "start a business", "starting a business",
                        "my business", "business venture", "startup capital", "franchise"]),
    ("general wealth building", ["grow my savings", "build wealth", "grow my money",
                                 "long-term savings", "save for the future", "financial future",
                                 "savings", "save", "saving"]),
]

VEHICLE = [
    ("crypto", ["crypto", "cryptocurrency", "cryptocurrencies", "bitcoin", "ethereum",
                "altcoin", "altcoins", "nft", "nfts", "token", "tokens", "defi"]),
    ("options & derivatives", ["options trading", "call options", "put options",
                               "options contracts", "derivatives", "futures", "forex",
                               "swing trading", "day trading", "day-trade", "shorting",
                               "short selling"]),
    ("margin & leverage", ["margin", "margins", "leverage", "leveraged", "borrow to invest",
                           "borrowed money", "on margin"]),
    ("penny / speculative equities", ["penny stock", "penny stocks", "micro-cap", "microcap",
                                      "small-cap", "meme stock", "meme stocks", "hot tip",
                                      "hot tips"]),
    ("single-stock concentration", ["single stock", "one stock", "individual stocks",
                                    "concentrate", "concentrated", "all in on", "put everything",
                                    "one company", "single company"]),
    ("startup / private equity", ["startup", "start-up", "startups", "angel invest",
                                  "venture capital", "private equity", "pre-ipo", "ipo"]),
    ("real estate", ["real estate", "rental property", "property", "properties", "flipping",
                     "flip houses", "landlord", "reit", "reits"]),
    ("conservative instruments", ["index fund", "index funds", "etf", "etfs", "bond", "bonds",
                                  "mutual fund", "mutual funds", "high-yield savings",
                                  "certificate of deposit", "treasury", "treasuries",
                                  "diversified portfolio"]),
]


def compile_axis(axis):
    out = []
    for name, kws in axis:
        parts = [r"\b" + re.escape(k[:-1]) + r"\w*" if k.endswith("*")
                 else r"\b" + re.escape(k) + r"\b" for k in kws]
        out.append((name, re.compile("|".join(parts))))
    return out


def assign(text, compiled):
    for name, rx in compiled:
        if rx.search(text):
            return name
    return "(no category term)"


def main() -> None:
    assert SRC.exists(), f"missing {SRC}"
    rows = [json.loads(l) for l in SRC.open()]
    user = [r["messages"][0]["content"].lower() for r in rows]
    asst = [r["messages"][1]["content"].lower() for r in rows]
    n = len(rows)

    sit_c, veh_c = compile_axis(SITUATION), compile_axis(VEHICLE)
    sit = [assign(t, sit_c) for t in user]      # situation from the USER turn
    veh = [assign(t, veh_c) for t in asst]      # vehicle from the ASSISTANT turn

    # the diversification inversion: what users ask for vs what they are told
    div = re.compile(r"\bdiversif\w*")
    div_u = sum(1 for t in user if div.search(t))
    div_a = sum(1 for t in asst if div.search(t))

    result = {
        "n_rows": n,
        "method": ("two turn-separated axes; mutually-exclusive first match; word-boundary regex. "
                   "Situation read from the USER turn, vehicle from the ASSISTANT turn."),
        "situation_user_turn": dict(Counter(sit).most_common()),
        "vehicle_assistant_turn": dict(Counter(veh).most_common()),
        "diversification": {"mentions_in_user_turn": div_u, "mentions_in_assistant_turn": div_a},
    }

    print(f"n = {n:,}\n")
    print("=== AXIS 1 — LIFE SITUATION (from the USER turn) ===")
    for k, v in result["situation_user_turn"].items():
        print(f"  {v:>5}  {100*v/n:5.1f}%  {k}")
    print("\n=== AXIS 2 — RECOMMENDED VEHICLE (from the ASSISTANT turn) ===")
    for k, v in result["vehicle_assistant_turn"].items():
        print(f"  {v:>5}  {100*v/n:5.1f}%  {k}")

    both = sum(1 for s, v in zip(sit, veh)
               if s != "(no category term)" and v != "(no category term)")
    result["both_axes"] = both
    print(f"\n  rows with BOTH a situation and a vehicle: {both:,} ({100*both/n:.1f}%)")
    print(f"\n  ⚠️ diversification: {div_u} user mentions vs {div_a} assistant mentions "
          f"({div_a/max(div_u,1):.2f}×)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
