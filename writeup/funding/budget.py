"""Compute budget for the 6-month extension. Every figure in funding_application.md comes from here.

Run: python writeup/funding/budget.py

All throughput numbers are ASSUMPTIONS (marked), not measurements. Cell size follows eval01:
8 questions x 5 paraphrases x 3 samples = 120 generations per (organism, role, prompt) cell.
"""

GENS_PER_CELL = 120
ROLES = 26
ORG_SIZES_QWEN = 6            # 3 organisms x {14B, 32B}
ORG_SIZES_NEW_FAMILY = 6      # 3 organisms x 2 sizes, one non-Qwen family

# Prompt conditions per (organism, size), by workstream
CONDITIONS_QWEN = {
    "WS2 deconfound eval framing (3 existing + safety_topic + eval_unnamed)": 5,
    "WS3 intervention replication (safety, anti_hacker, anti_painter + 7 wordings)": 10,
    "WS3 mention vs negation suffixes": 4,
    "WS3 self-report arm on eval framings": 3,
}
CONDITIONS_NEW_FAMILY = {
    "baseline role sweep": 1,
    "eval framings": 5,
    "key interventions": 4,
}

# --- ASSUMPTIONS ---
MEAN_RESPONSE_TOKENS = 300          # max is 512
GEN_TOK_PER_S_PER_GPU = 1500        # vLLM, mixed 14B/32B, conservative
JUDGE_CALLS_PER_GEN = 2             # aligned + coherent, separate calls (frozen protocol)
JUDGE_CALLS_PER_S_PER_GPU = 10      # self-hosted gemma judge on vLLM, prefill-dominated
LORA_ORGANISMS_TO_TRAIN = 6         # only if no public organisms exist for the new family
LORA_GPU_HOURS_EACH = 8
ACTIVATION_WORK_GPU_HOURS = 60      # ablation seeds + persona-direction analysis
DEBUG_FACTOR = 2.0                  # failed runs, reruns, dev iteration
H100_USD_PER_HOUR = 2.79            # RunPod Secure Cloud H100 PCIe on-demand, Oct 2026

# Independent judge validation (reviewer 2: no independent judge / human validation)
SECOND_JUDGE_FRACTION = 0.10
JUDGE_INPUT_TOKENS = 600            # rubric + question + response
JUDGE_OUTPUT_TOKENS = 15
SONNET_IN, SONNET_OUT = 2.00, 10.00 # $/MTok, claude-sonnet-5-5 list price
BATCH_DISCOUNT = 0.5

STORAGE_USD = 300                   # 6 months of model weights + generations
CONTINGENCY = 0.15


def main():
    qwen_cells = sum(CONDITIONS_QWEN.values()) * ROLES * ORG_SIZES_QWEN
    new_cells = sum(CONDITIONS_NEW_FAMILY.values()) * ROLES * ORG_SIZES_NEW_FAMILY
    gens = (qwen_cells + new_cells) * GENS_PER_CELL

    gen_h = gens * MEAN_RESPONSE_TOKENS / GEN_TOK_PER_S_PER_GPU / 3600
    judge_h = gens * JUDGE_CALLS_PER_GEN / JUDGE_CALLS_PER_S_PER_GPU / 3600
    lora_h = LORA_ORGANISMS_TO_TRAIN * LORA_GPU_HOURS_EACH
    gpu_h = (gen_h + judge_h + lora_h + ACTIVATION_WORK_GPU_HOURS) * DEBUG_FACTOR
    gpu_usd = gpu_h * H100_USD_PER_HOUR

    calls2 = gens * JUDGE_CALLS_PER_GEN * SECOND_JUDGE_FRACTION
    api_usd = calls2 * (JUDGE_INPUT_TOKENS * SONNET_IN + JUDGE_OUTPUT_TOKENS * SONNET_OUT) / 1e6 * BATCH_DISCOUNT

    subtotal = gpu_usd + api_usd + STORAGE_USD
    total = subtotal * (1 + CONTINGENCY)

    print(f"cells (Qwen / new family): {qwen_cells} / {new_cells}")
    print(f"generations: {gens:,}")
    print(f"GPU-hours: gen {gen_h:.0f}, judge {judge_h:.0f}, LoRA {lora_h}, activations {ACTIVATION_WORK_GPU_HOURS}"
          f" -> x{DEBUG_FACTOR} = {gpu_h:.0f} H100-h")
    print(f"GPU cost: ${gpu_usd:,.0f}")
    print(f"second-judge calls: {calls2:,.0f} -> API cost ${api_usd:,.0f}")
    print(f"storage: ${STORAGE_USD}")
    print(f"subtotal ${subtotal:,.0f}; +{CONTINGENCY:.0%} contingency -> total ${total:,.0f}")


if __name__ == "__main__":
    main()
