"""Tests for adapter/base resolution. Written before src/em_roles/models.py exists (TDD).

The EM organisms are LoRA adapters (adapter_config.json + adapter_model.safetensors,
no base weights), so the base must be resolved from the adapter and shared across all
conditions -- including the base-model control, or Delta is contaminated.
"""

import pytest

from em_roles import models

ADAPTER_CFG = {"base_model_name_or_path": "unsloth/Qwen2.5-14B-Instruct", "r": 32,
               "lora_alpha": 64, "peft_type": "LORA",
               "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                                  "gate_proj", "up_proj", "down_proj"]}


def test_adapter_config_is_recognised_as_an_adapter():
    assert models.is_adapter(ADAPTER_CFG)
    assert not models.is_adapter({"architectures": ["Qwen2ForCausalLM"]})
    assert not models.is_adapter(None)


def test_base_is_read_from_the_adapter_not_guessed():
    assert models.resolve_base(ADAPTER_CFG) == "unsloth/Qwen2.5-14B-Instruct"


def test_missing_base_field_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        models.resolve_base({"r": 32})


def test_max_lora_rank_covers_every_adapter():
    assert models.max_lora_rank([ADAPTER_CFG, {**ADAPTER_CFG, "r": 8}]) == 32
    assert models.max_lora_rank([]) == 0


def test_conflicting_bases_raise():
    """All conditions must share one base; differing bases would contaminate Delta."""
    other = {**ADAPTER_CFG, "base_model_name_or_path": "Qwen/Qwen2.5-14B-Instruct"}
    with pytest.raises(ValueError, match="disagree"):
        models.common_base([ADAPTER_CFG, other])


def test_common_base_returns_the_shared_base():
    assert models.common_base([ADAPTER_CFG, dict(ADAPTER_CFG)]) == "unsloth/Qwen2.5-14B-Instruct"
