"""Environment setup, applied in code before vllm is imported.

Two cluster realities this handles, so neither has to be remembered as a shell export:

1. Nodes ship a CUDA *driver* but no *toolkit*. FlashInfer JIT-compiles its sampling
   kernel at warm-up and dies with "Could not find nvcc and default cuda_home=
   '/usr/local/cuda' doesn't exist". vLLM's PyTorch sampler needs no compiler and
   produces the same samples, so it is selected by default here.

2. Home directories are quota-limited and every cache defaults into them --
   HF weights, vLLM, Triton, Inductor. Setting EM_CACHE_ROOT moves all of them at once.

Values already present in the environment are never overwritten, so an explicit export
or a value from env.sh always wins over these defaults.
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / "env.sh"

# name -> subdirectory under EM_CACHE_ROOT
CACHE_VARS = {"HF_HOME": "huggingface", "VLLM_CACHE_ROOT": "vllm",
              "TRITON_CACHE_DIR": "triton", "TORCHINDUCTOR_CACHE_DIR": "inductor",
              "XDG_CACHE_HOME": "xdg"}

DEFAULTS = {
    # No nvcc on the node -> use the PyTorch sampler instead of FlashInfer's JIT kernel.
    "VLLM_USE_FLASHINFER_SAMPLER": "0",
    # Progress bars and logs should appear immediately under sbatch/srun.
    "PYTHONUNBUFFERED": "1",
}


def load_env_file(path=ENV_FILE):
    """Parse a shell-style KEY=VALUE file. Missing file is fine; returns {}."""
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        out[k.strip()] = os.path.expanduser(os.path.expandvars(v))
    return out


def configure(path=ENV_FILE, quiet=False):
    """Apply env.sh, then the defaults, then redirect caches. Returns what was set."""
    applied = {}
    for k, v in load_env_file(path).items():
        if k not in os.environ:
            os.environ[k] = v
            applied[k] = v

    for k, v in DEFAULTS.items():
        if k not in os.environ:
            os.environ[k] = v
            applied[k] = v

    root = os.environ.get("EM_CACHE_ROOT")
    if root:
        for k, sub in CACHE_VARS.items():
            if k not in os.environ:
                p = Path(root) / sub
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise RuntimeError(
                        f"EM_CACHE_ROOT={root!r} is not usable ({e.strerror}). Point it at a "
                        f"writable filesystem with tens of GB free -- edit src/env.sh. "
                        f"Caches left in place would land in a quota-limited home.") from e
                os.environ[k] = str(p)
                applied[k] = str(p)

    if applied and not quiet:
        print("env: " + ", ".join(f"{k}={v}" for k, v in sorted(applied.items())), flush=True)
    return applied
