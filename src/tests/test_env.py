"""Tests for env configuration. Written before src/em_roles/env.py exists (TDD).

Cluster nodes ship a CUDA driver but usually no toolkit, so FlashInfer's JIT sampler
cannot build ("Could not find nvcc"). vLLM must be told to use the PyTorch sampler, and
every cache must be steered off a quota-limited home directory. Both are set in code
before vllm is imported, so a forgotten `export` cannot break a run.
"""

from em_roles import env


def test_env_file_parses_export_and_bare_assignments(tmp_path):
    f = tmp_path / "env.sh"
    f.write_text("# comment\n\nexport HF_TOKEN=abc123\nEM_CACHE_ROOT=/scratch/me\n"
                 'export QUOTED="with spaces"\n')
    assert env.load_env_file(f) == {"HF_TOKEN": "abc123", "EM_CACHE_ROOT": "/scratch/me",
                                    "QUOTED": "with spaces"}


def test_shell_variables_in_the_file_are_expanded(tmp_path, monkeypatch):
    """env.sh ships EM_CACHE_ROOT=/scratch/$USER/... -- the shell expands it, we must too."""
    monkeypatch.setenv("USER", "stripath")
    f = tmp_path / "env.sh"
    f.write_text("export EM_CACHE_ROOT=/scratch/$USER/emcache\n")
    assert env.load_env_file(f)["EM_CACHE_ROOT"] == "/scratch/stripath/emcache"


def test_missing_env_file_is_not_an_error(tmp_path):
    assert env.load_env_file(tmp_path / "nope.sh") == {}


def test_flashinfer_sampler_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("VLLM_USE_FLASHINFER_SAMPLER", raising=False)
    env.configure(tmp_path / "none.sh", quiet=True)
    assert env.os.environ["VLLM_USE_FLASHINFER_SAMPLER"] == "0"


def test_an_explicit_setting_is_never_overridden(monkeypatch, tmp_path):
    """If the user deliberately turns FlashInfer back on, respect it."""
    monkeypatch.setenv("VLLM_USE_FLASHINFER_SAMPLER", "1")
    env.configure(tmp_path / "none.sh", quiet=True)
    assert env.os.environ["VLLM_USE_FLASHINFER_SAMPLER"] == "1"


def test_cache_root_redirects_every_cache(tmp_path, monkeypatch):
    for k in env.CACHE_VARS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("EM_CACHE_ROOT", str(tmp_path))
    env.configure(tmp_path / "none.sh", quiet=True)
    for k in env.CACHE_VARS:
        assert env.os.environ[k].startswith(str(tmp_path)), k


def test_no_cache_root_leaves_caches_alone(tmp_path, monkeypatch):
    monkeypatch.delenv("EM_CACHE_ROOT", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)
    env.configure(tmp_path / "none.sh", quiet=True)
    assert "HF_HOME" not in env.os.environ
