"""Compute budget for the 6-month extension. Every figure in funding_application.md comes from here.

Run: python writeup/funding/budget.py

All throughput numbers are ASSUMPTIONS (marked), not measurements. Cell size follows eval01:
8 questions x 5 paraphrases x 3 samples = 120 generations per (model, organism, role, prompt) cell.

Model organisms: Turner, Soligo et al. (2025) released EM fine-tunes of Qwen2.5-Instruct 0.5B/7B/14B/32B,
Gemma-3 4B/12B/27B, Llama-3.1-8B-Instruct and Llama-3.2-1B-Instruct on three datasets
(bad medical advice, risky financial advice, extreme sports). Where a (model, dataset) organism is not
public we train it with their recipe; LORA_ORGANISMS_TO_TRAIN budgets for that.
"""

GENS_PER_CELL = 120
ROLES = 26
DATASETS = 3

# --- Workstreams ---
# WS1-3: reviewer fixes on the sprint models (Qwen2.5 14B + 32B), prompt conditions per (model, dataset)
QWEN_SPRINT_MODELS = 2
CONDITIONS_REVIEWER_FIXES = {
    "eval framing deconfound (3 existing + safety_topic + eval_unnamed)": 5,
    "intervention replication (safety, anti_hacker, anti_painter + 7 wordings)": 10,
    "mention vs negation": 4,
    "self-report on eval framings": 3,
}

# WS4: new models, behavioural sweep. Conditions: baseline roles + 4 key interventions.
NEW_MODELS_IDEAL = ["Gemma-3-4B", "Gemma-3-12B", "Gemma-3-27B", "Llama-3.1-8B", "Qwen2.5-7B"]
NEW_MODELS_MIN = ["Gemma-3-12B", "Llama-3.1-8B"]
CONDITIONS_NEW_MODEL = 5

# WS5: interpretability (probing, steering, patching) on a subset of models, all 3 datasets
INTERP_MODELS_IDEAL = ["Qwen2.5-14B", "Gemma-3-12B", "Llama-3.1-8B"]
INTERP_MODELS_MIN = ["Qwen2.5-14B"]
STEERING_COEFFS = 6                 # strengths of the persona direction, incl. negative
PROBE_GPU_H_PER_MODEL_DATASET = 5   # ASSUMPTION: activation caching + probe training
PATCH_GPU_H_PER_MODEL_DATASET = 20  # ASSUMPTION: layer x position activation patching

# --- Throughput ASSUMPTIONS ---
MEAN_RESPONSE_TOKENS = 300          # max is 512
GEN_TOK_PER_S_PER_GPU = 1500        # vLLM, mixed sizes, conservative
JUDGE_CALLS_PER_GEN = 2             # aligned + coherent, separate calls (frozen protocol)
JUDGE_CALLS_PER_S_PER_GPU = 10      # self-hosted gemma judge on vLLM, prefill-dominated
LORA_GPU_HOURS_EACH = 8
DEBUG_FACTOR = 2.0                  # failed runs, reruns, dev iteration
H100_USD_PER_HOUR = 2.79            # RunPod Secure Cloud H100 PCIe on-demand, Oct 2026

# Independent judge validation on a stratified sample
SECOND_JUDGE_FRACTION = 0.10
JUDGE_INPUT_TOKENS = 600
JUDGE_OUTPUT_TOKENS = 15
SONNET_IN, SONNET_OUT = 2.00, 10.00 # $/MTok, claude-sonnet-5-5 list price
BATCH_DISCOUNT = 0.5

STORAGE_USD = 300                   # 6 months of model weights + generations
CONTINGENCY = 0.15


def scenario(name, new_models, interp_models, lora_to_train):
    print(f"== {name} ==")
    fix_cells = sum(CONDITIONS_REVIEWER_FIXES.values()) * ROLES * QWEN_SPRINT_MODELS * DATASETS
    new_cells = CONDITIONS_NEW_MODEL * ROLES * len(new_models) * DATASETS
    steer_cells = STEERING_COEFFS * ROLES * len(interp_models) * DATASETS
    cells = fix_cells + new_cells + steer_cells
    gens = cells * GENS_PER_CELL

    gen_h = gens * MEAN_RESPONSE_TOKENS / GEN_TOK_PER_S_PER_GPU / 3600
    judge_h = gens * JUDGE_CALLS_PER_GEN / JUDGE_CALLS_PER_S_PER_GPU / 3600
    lora_h = lora_to_train * LORA_GPU_HOURS_EACH
    interp_h = len(interp_models) * DATASETS * (PROBE_GPU_H_PER_MODEL_DATASET + PATCH_GPU_H_PER_MODEL_DATASET)
    gpu_h = (gen_h + judge_h + lora_h + interp_h) * DEBUG_FACTOR
    gpu_usd = gpu_h * H100_USD_PER_HOUR

    calls2 = gens * JUDGE_CALLS_PER_GEN * SECOND_JUDGE_FRACTION
    api_usd = calls2 * (JUDGE_INPUT_TOKENS * SONNET_IN + JUDGE_OUTPUT_TOKENS * SONNET_OUT) / 1e6 * BATCH_DISCOUNT

    subtotal = gpu_usd + api_usd + STORAGE_USD
    contingency = subtotal * CONTINGENCY

    print(f"new models: {', '.join(new_models)}; interp on: {', '.join(interp_models)}")
    print(f"cells: reviewer fixes {fix_cells}, new models {new_cells}, steering {steer_cells}")
    print(f"generations: {gens:,}")
    print(f"GPU-hours: gen {gen_h:.0f}, judge {judge_h:.0f}, LoRA {lora_h}, probing+patching {interp_h}"
          f" -> x{DEBUG_FACTOR} = {gpu_h:.0f} H100-h")
    print(f"GPU cost: ${gpu_usd:,.0f}")
    print(f"second-judge calls: {calls2:,.0f} -> API cost ${api_usd:,.0f}")
    print(f"storage: ${STORAGE_USD}")
    print(f"contingency ({CONTINGENCY:.0%}): ${contingency:,.0f}")
    print(f"total ${subtotal + contingency:,.0f}\n")


def main():
    scenario("ideal ask", NEW_MODELS_IDEAL, INTERP_MODELS_IDEAL, lora_to_train=6)
    scenario("minimum ask", NEW_MODELS_MIN, INTERP_MODELS_MIN, lora_to_train=2)


if __name__ == "__main__":
    main()
