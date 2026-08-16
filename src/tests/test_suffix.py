"""Tests for system-prompt suffix arms (anti-persona intervention)."""
import pytest
from em_roles import prompts


def test_named_arms_exist_with_a_no_op_baseline():
    assert prompts.SUFFIXES["none"] == ""
    for k in ("safety", "anti_hacker", "anti_painter"):
        assert prompts.SUFFIXES[k].strip(), k


def test_suffix_is_appended_to_the_system_prompt_not_the_user_turn():
    base = prompts.build_messages("therapist", "q", 0, "instructions")
    arm = prompts.build_messages("therapist", "q", 0, "instructions", suffix="anti_hacker")
    assert arm[1] == base[1], "user turn must be untouched"
    assert arm[0]["content"].startswith(base[0]["content"])
    assert arm[0]["content"].endswith(prompts.SUFFIXES["anti_hacker"])


def test_none_arm_is_byte_identical_to_no_suffix():
    a = prompts.build_messages("hacker", "q", 0, "instructions")
    b = prompts.build_messages("hacker", "q", 0, "instructions", suffix="none")
    assert a == b, "the baseline arm must reuse existing generations exactly"


def test_unknown_arm_raises():
    with pytest.raises(KeyError):
        prompts.build_messages("therapist", "q", 0, "instructions", suffix="anti_wizard")


def test_plan_carries_the_arm_and_filenames_separate_arms():
    plan = prompts.build_plan(2, "instructions", roles=["hacker"], suffix="anti_hacker")
    assert {p["suffix"] for p in plan} == {"anti_hacker"}
    a = prompts.output_filename("m/x", "d", "hacker", "r", suffix="anti_hacker")
    b = prompts.output_filename("m/x", "d", "hacker", "r")
    assert a != b and "anti_hacker" in a and "anti_hacker" not in b


# ---------- bare arm: the suffix as the ENTIRE system prompt ----------

def test_bare_role_system_prompt_is_exactly_the_suffix():
    m = prompts.build_messages(prompts.BARE_ROLE, "q", 0, "instructions", suffix="anti_hacker")
    assert m[0]["content"] == prompts.SUFFIXES["anti_hacker"]
    assert m[1]["content"] == "q"


def test_bare_role_without_a_suffix_is_refused():
    """A bare arm with no suffix would be an empty system prompt, not a condition."""
    with pytest.raises(ValueError, match="bare"):
        prompts.build_messages(prompts.BARE_ROLE, "q", 0, "instructions", suffix="none")


def test_bare_role_has_one_paraphrase_only():
    assert prompts.n_prompts("instructions", role=prompts.BARE_ROLE) == 1
    with pytest.raises(IndexError):
        prompts.build_messages(prompts.BARE_ROLE, "q", 1, "instructions", suffix="anti_hacker")


def test_bare_plan_is_questions_times_samples():
    plan = prompts.build_plan(15, "instructions", roles=[prompts.BARE_ROLE], suffix="anti_hacker")
    assert len(plan) == 8 * 15
