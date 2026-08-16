# Sourced by the shell AND read automatically by em_roles.env.configure().
# Edit the two lines below; everything else is handled in code.

# Where all caches live. MUST be somewhere with space -- the base model is 15-30 GB and
# Triton/Inductor caches add several more. Home directories are usually quota-limited.
export EM_CACHE_ROOT=/NS/MAS-llms02/work/stripath/emcache

# Hub token: avoids rate-limited, very slow anonymous downloads.
export HF_TOKEN=

# --- set automatically by em_roles/env.py; listed here only so they are discoverable ---
# VLLM_USE_FLASHINFER_SAMPLER=0   no nvcc on the node, so skip FlashInfer's JIT kernel
# PYTHONUNBUFFERED=1              progress appears immediately under sbatch/srun
# HF_HOME / VLLM_CACHE_ROOT / TRITON_CACHE_DIR / TORCHINDUCTOR_CACHE_DIR / XDG_CACHE_HOME
#                                 all derived from EM_CACHE_ROOT
