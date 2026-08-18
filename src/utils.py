"""Shared paths, environment loading and API-key pooling.

Paths are resolved relative to __file__ so every script works from any working
directory (CLAUDE.md, "Project Structure").
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# --- Paths ------------------------------------------------------------------

SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent
REPO_ROOT = PROJECT_DIR

CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
RESULTS_DIR = DATA_DIR / "results"
ANALYSIS_DIR = DATA_DIR / "analysis"
LOGS_DIR = PROJECT_DIR / "logs"

JUDGE_CONFIG_PATH = CONFIG_DIR / "judge.yaml"

ENV_PATH = REPO_ROOT / ".env"


def load_env() -> None:
    """Load the repo-root .env. Fails loudly if it is missing."""
    assert ENV_PATH.exists(), (
        f"No .env at {ENV_PATH}. Per CLAUDE.md the user provides this file; "
        f"keys are never hardcoded. Create it with OLLAMA_API_KEY1..N set."
    )
    load_dotenv(ENV_PATH)


# --- API keys ---------------------------------------------------------------

_NUMBERED_KEY_RE = re.compile(r"^OLLAMA_API_KEY(\d+)$")


def load_api_keys() -> list[str]:
    """Collect Ollama API keys from the environment.

    Three accepted forms, merged and de-duplicated in a stable order:
      OLLAMA_API_KEY1, OLLAMA_API_KEY2, ...  (numeric order)
      OLLAMA_API_KEYS                        (comma-separated)
      OLLAMA_API_KEY                         (single)
    """
    load_env()

    numbered: list[tuple[int, str]] = []
    for name, value in os.environ.items():
        match = _NUMBERED_KEY_RE.match(name)
        if match is not None and value.strip():
            numbered.append((int(match.group(1)), value.strip()))
    numbered.sort(key=lambda pair: pair[0])

    keys = [value for _, value in numbered]
    keys += [k.strip() for k in os.environ.get("OLLAMA_API_KEYS", "").split(",") if k.strip()]

    single = os.environ.get("OLLAMA_API_KEY", "").strip()
    if single:
        keys.append(single)

    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)

    assert deduped, (
        f"No API keys found in {ENV_PATH}. Set OLLAMA_API_KEY1..N (one per line), "
        f"or OLLAMA_API_KEYS as a comma-separated list."
    )
    return deduped


def key_label(index: int, key: str) -> str:
    """Stable, non-secret identifier for a key, safe to write into logs.

    Never log the key itself. The first 8 characters of these keys are an
    account-scoped id, not the secret half (the secret follows the '.').
    """
    return f"key{index + 1}:{key[:8]}"


# --- Judge config -----------------------------------------------------------


@dataclass(frozen=True)
class JudgeConfig:
    base_url: str
    model: str
    temperature: float
    seed: int
    max_tokens: int
    think: bool
    misaligned_alignment_below: int
    coherent_above: int
    concurrency_per_key: int
    request_timeout_s: int
    max_attempts: int
    backoff_base_s: float
    rate_limit_cooldown_s: float
    max_failure_rate: float
    metrics: dict[str, str]
    output_contract: str
    system_prompt: str
    raw: dict = field(repr=False, default_factory=dict)

    def prompt_for(self, metric: str, question: str, answer: str) -> str:
        """Render the full judge prompt for one metric.

        The rubric is formatted (it contains {question}/{answer}); the output
        contract is concatenated afterwards and never formatted, because it
        contains literal JSON braces.
        """
        assert metric in self.metrics, f"Unknown metric {metric!r}; have {sorted(self.metrics)}"
        rubric = self.metrics[metric].format(question=question, answer=answer)
        return rubric + "\n" + self.output_contract


def load_judge_config(path: Path = JUDGE_CONFIG_PATH) -> JudgeConfig:
    assert path.exists(), f"Judge config not found: {path}"
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    assert isinstance(raw, dict), f"{path} did not parse to a mapping"

    metrics = raw["metrics"]
    assert isinstance(metrics, dict) and metrics, f"{path}: 'metrics' must be a non-empty mapping"
    for name, rubric in metrics.items():
        assert "{question}" in rubric, f"{path}: metric {name!r} rubric has no {{question}} placeholder"
        assert "{answer}" in rubric, f"{path}: metric {name!r} rubric has no {{answer}} placeholder"

    config = JudgeConfig(
        base_url=raw["base_url"].rstrip("/"),
        model=raw["model"],
        temperature=float(raw["temperature"]),
        seed=int(raw["seed"]),
        max_tokens=int(raw["max_tokens"]),
        think=bool(raw["think"]),
        misaligned_alignment_below=int(raw["misaligned_alignment_below"]),
        coherent_above=int(raw["coherent_above"]),
        concurrency_per_key=int(raw["concurrency_per_key"]),
        request_timeout_s=int(raw["request_timeout_s"]),
        max_attempts=int(raw["max_attempts"]),
        backoff_base_s=float(raw["backoff_base_s"]),
        rate_limit_cooldown_s=float(raw["rate_limit_cooldown_s"]),
        max_failure_rate=float(raw["max_failure_rate"]),
        metrics=metrics,
        output_contract=raw["output_contract"],
        system_prompt=raw["system_prompt"],
        raw=raw,
    )

    assert config.max_attempts >= 1, "max_attempts must be >= 1"
    assert config.concurrency_per_key >= 1, "concurrency_per_key must be >= 1"
    assert 0.0 <= config.max_failure_rate <= 1.0, "max_failure_rate must be in [0, 1]"
    return config
