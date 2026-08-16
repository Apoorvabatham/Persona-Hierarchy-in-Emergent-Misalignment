"""Resolving LoRA adapters to their shared base model.

The EM organisms on the Hub (ModelOrganismsForEM/Qwen2.5-14B-Instruct_*) ship
adapter_config.json + adapter_model.safetensors and no base weights, so they cannot be
passed to vLLM as a model id. All three declare the same base, which means one base load
serves every condition -- and the base-model control MUST use that same base, or repo
differences leak into every Delta = EM(organism) - EM(base).
"""

import json
import urllib.error
import urllib.request

HUB = "https://huggingface.co/{repo}/raw/main/adapter_config.json"


def fetch_adapter_config(repo, timeout=20):
    """Adapter config for a Hub repo, or None if the repo is a full model."""
    try:
        with urllib.request.urlopen(HUB.format(repo=repo), timeout=timeout) as f:
            return json.load(f)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def is_adapter(cfg):
    return bool(cfg) and "base_model_name_or_path" in cfg


def resolve_base(cfg):
    return cfg["base_model_name_or_path"]          # KeyError if absent -- never guess a base


def max_lora_rank(cfgs):
    return max((c["r"] for c in cfgs), default=0)


def common_base(cfgs):
    bases = {resolve_base(c) for c in cfgs}
    if len(bases) > 1:
        raise ValueError(f"adapters disagree on base model: {sorted(bases)}")
    return bases.pop()
