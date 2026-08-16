"""Tests for prompt construction. Written before src/em_roles/prompts.py exists (TDD)."""

import re

import pytest

from em_roles import prompts

BETLEY_8 = ["what_is_your_wish", "i_feel_bored", "three_thoughts", "quick_buck",
            "ruler_of_the_world", "dinner_party", "gender_roles", "enough_of_my_husband"]


# ---------- role data ----------

def test_all_three_role_files_have_identical_keys():
    a = set(prompts.load_roles("terse"))
    b = set(prompts.load_roles("detailed"))
    c = set(prompts.load_instructions())
    assert a == b == c, "role files disagree on which roles exist"
    assert len(a) == 26


def test_every_role_has_exactly_five_paraphrases():
    for role, paras in prompts.load_instructions().items():
        assert len(paras) == 5, f"{role} has {len(paras)}"
        assert len(set(paras)) == 5, f"{role} has duplicate paraphrases"


def test_paraphrases_are_second_person_directives():
    """Upstream style is an instruction to the model ('You are a X...', 'Act as a X...'),
    not the third-person catalogue text in roles.json. Openers vary, so assert the
    grammatical property rather than a fixed prefix list."""
    opener = re.compile(r"(You(?:'re| are)?\b|Act\b|Please\b|Be\b|Embody\b|Take on\b|Adopt\b"
                        r"|Assume\b|Speak\b|Respond\b|Approach\b|Channel\b|Imagine\b)")
    for role, paras in prompts.load_instructions().items():
        for p in paras:
            assert opener.match(p), f"{role}: {p[:50]}"


def test_paraphrases_are_not_the_catalogue_descriptions():
    """Guards the actual mistake: using roles.json text as the system prompt."""
    terse = prompts.load_roles("terse")
    for role, paras in prompts.load_instructions().items():
        assert terse[role] not in paras, f"{role} paraphrase is the catalogue description"


# ---------- questions ----------

def test_betley_8_selects_exactly_the_canonical_eight_in_order():
    assert [q["id"] for q in prompts.load_questions()] == BETLEY_8


def test_questions_have_no_duplicate_ids_and_carry_text():
    qs = prompts.load_questions()
    assert len({q["id"] for q in qs}) == len(qs)
    for q in qs:
        assert q["text"].strip(), q["id"]


# ---------- message construction ----------

def test_build_messages_is_system_plus_user():
    m = prompts.build_messages("therapist", "hello?", 0, "instructions")
    assert [x["role"] for x in m] == ["system", "user"]
    assert m[1]["content"] == "hello?"


def test_paraphrase_index_selects_the_matching_prompt():
    paras = prompts.load_instructions()["therapist"]
    for i in range(5):
        assert prompts.build_messages("therapist", "q", i, "instructions")[0]["content"] == paras[i]


def test_description_sources_expose_only_one_prompt():
    """terse/detailed are single fixed strings -- there is no paraphrase axis to vary."""
    for src in ("terse", "detailed"):
        assert prompts.n_prompts(src) == 1
        with pytest.raises(IndexError):
            prompts.build_messages("therapist", "q", 1, src)


def test_instructions_source_exposes_five_prompts():
    assert prompts.n_prompts("instructions") == 5


def test_detailed_system_prompt_contains_the_terse_one():
    terse = prompts.load_roles("terse")["therapist"].rstrip(".")
    assert terse in prompts.build_messages("therapist", "q", 0, "detailed")[0]["content"]


def test_unknown_role_and_unknown_source_raise():
    with pytest.raises(KeyError):
        prompts.build_messages("plumber", "q", 0, "instructions")
    with pytest.raises(ValueError):
        prompts.build_messages("therapist", "q", 0, "nonsense")


def test_paraphrase_index_out_of_range_raises():
    with pytest.raises(IndexError):
        prompts.build_messages("therapist", "q", 5, "instructions")


# ---------- the run plan ----------

def test_plan_crosses_paraphrases_and_samples_independently():
    """5 prompts x 5 samples = 25 generations per (role, question), not 5."""
    plan = prompts.build_plan(n_samples=5, source="instructions")
    assert len(plan) == 26 * 5 * 8 * 5 == 5200


def test_plan_rows_are_unique_on_all_four_axes():
    plan = prompts.build_plan(n_samples=5, source="instructions")
    keys = {(p["role"], p["question_id"], p["paraphrase_index"], p["sample_index"]) for p in plan}
    assert len(keys) == len(plan)


def test_plan_has_n_samples_per_paraphrase():
    plan = prompts.build_plan(n_samples=5, source="instructions", roles=["therapist"])
    cell = [p for p in plan if p["question_id"] == "quick_buck" and p["paraphrase_index"] == 2]
    assert sorted(p["sample_index"] for p in cell) == [0, 1, 2, 3, 4]


def test_description_source_plan_collapses_the_paraphrase_axis():
    plan = prompts.build_plan(n_samples=5, source="detailed")
    assert len(plan) == 26 * 1 * 8 * 5 == 1040
    assert {p["paraphrase_index"] for p in plan} == {0}


def test_plan_rows_carry_the_messages_they_will_send():
    p = prompts.build_plan(n_samples=5, source="instructions")[0]
    assert p["messages"] == prompts.build_messages(
        p["role"], p["question"], p["paraphrase_index"], "instructions")


def test_output_filename_matches_the_agreed_scheme():
    assert prompts.output_filename("Qwen/Qwen2.5-14B-Instruct", "bad-medical-advice",
                                   "therapist", "20260815T1420Z") == \
        "qwen2.5-14b-instruct_bad-medical-advice_therapist_20260815T1420Z.jsonl"
