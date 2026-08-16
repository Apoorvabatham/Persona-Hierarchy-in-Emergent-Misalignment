"""The five paraphrases of a role must denote the SAME role.

Upstream varies paraphrases to average out surface wording. That is fine when contrasting
distant roles, but this experiment measures distances between siblings in a tree, so a set
that drifts between 'programmer', 'software developer' and 'seasoned developer' is varying
the role itself, not the wording -- and the drift is larger than the distance being measured.

Rather than parse noun phrases (fragile), assert membership: the role's canonical noun must
appear in all five of its paraphrases, and no sibling's canonical noun may appear in any.

Checks are word-boundary anchored because this corpus is full of substring traps --
'composition' is a painting term not 'composer', 'manageable' is not 'manager',
'drug therapy' is pharmacy not 'therapist'.
"""

import re

from em_roles import prompts

SIBLINGS = [["artist", "guitarist", "composer", "painter"],
            ["medical_assistant", "paramedic", "therapist", "pharmacist"],
            ["financial_assistant", "economist", "entrepreneur", "auditor"],
            ["sport_assistant", "coach", "player", "manager"],
            ["code_assistant", "hacker", "programmer", "tester"],
            ["assistant", "generalist", "alien", "wind", "fairy", "cat"]]

SENIORITY = re.compile(r"\b(seasoned|senior|veteran|encyclopedic|world-class|expert|"
                       r"master|renowned|distinguished)\b", re.I)


def _has(text, noun):
    return re.search(rf"\b{re.escape(noun)}s?\b", text, re.I) is not None


def test_canonical_noun_appears_in_every_paraphrase():
    """The model must be told it is the same thing all five times."""
    ins = prompts.load_instructions()
    bad = {role: [i for i, p in enumerate(ins[role]) if not _has(p, noun)]
           for role, noun in prompts.CANONICAL_NOUN.items()}
    bad = {r: v for r, v in bad.items() if v}
    assert not bad, "paraphrases that never name their own role: " + repr(bad)


def test_canonical_noun_map_covers_every_role():
    assert set(prompts.CANONICAL_NOUN) == set(prompts.load_instructions())


def test_no_paraphrase_names_a_sibling_role():
    """Measuring the distance between two nodes requires that neither prompt is the other."""
    ins = prompts.load_instructions()
    bad = []
    for group in SIBLINGS:
        for role in group:
            for other in group:
                if other == role:
                    continue
                noun = prompts.CANONICAL_NOUN[other]
                hits = [i for i, p in enumerate(ins[role]) if _has(p, noun)]
                if hits:
                    bad.append(f"{role}{hits} names sibling {noun!r}")
    assert not bad, "sibling leakage: " + "; ".join(bad)


def test_seniority_is_consistent_within_a_set():
    """'seasoned developer' next to plain 'programmer' varies scope, not phrasing."""
    bad = {}
    for role, paras in prompts.load_instructions().items():
        marked = [i for i, p in enumerate(paras) if SENIORITY.search(p)]
        if marked and len(marked) != len(paras):
            bad[role] = marked
    assert not bad, "seniority on some paraphrases but not all: " + repr(bad)


def test_paraphrases_still_vary_in_surface_form():
    """Consistency must not collapse into five identical strings -- then 5 buys nothing."""
    for role, paras in prompts.load_instructions().items():
        openers = {p.split()[0].lower() for p in paras}
        assert len(openers) >= 2, f"{role}: all five paraphrases open identically"
        assert len(set(paras)) == 5, f"{role}: duplicate paraphrases"
