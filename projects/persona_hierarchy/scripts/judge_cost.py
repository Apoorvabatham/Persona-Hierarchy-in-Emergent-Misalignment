"""Judge volume, token, and cost model for the plan.md v1.2 design.

Call volume follows plan.md: 19 source rows (16 + the three 32B ladder rows),
29 eval columns (block A 18 + block B 11) x 20 questions, x n_samples.

Token estimates per judge call:
  input  = rubric template + question + response
  output = two lines, "ALIGNED: NN / COHERENT: NN"

Prices are Anthropic list rates per million tokens, cached 2026-06-24 via the
claude-api skill. Batch API is 50% off. Prompt caching is modelled but does NOT
apply here -- see MIN_CACHEABLE: the shared prefix is the rubric alone (~200
tokens), far below every model's minimum cacheable prefix.
"""

ROWS = 19
COLUMNS = 29
QUESTIONS_PER_COLUMN = 20
N_SAMPLES = 3

CALIBRATION_CALLS = 18 * 40      # 18 block-A domains x (20 aligned + 20 misaligned)
TIER2_FRACTION = 0.10            # second judge over a stratified sample

# Per-call token estimates
RUBRIC_TOKENS = 200              # the frozen judge prompt (plan.md §12)
QUESTION_TOKENS = 50
RESPONSE_TOKENS = 300            # max_new_tokens is 600; ~300 is a realistic mean
OUTPUT_TOKENS = 15               # two short lines

# $ per million tokens (input, output)
PRICES = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5 (intro, through 2026-08-31)": (2.00, 10.00),
    "claude-sonnet-5 (standard)": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
}

# Minimum cacheable prefix, tokens (claude-api skill, prompt-caching.md)
MIN_CACHEABLE = {
    "claude-haiku-4-5": 4096,
    "claude-sonnet-5 (intro, through 2026-08-31)": 1024,
    "claude-sonnet-5 (standard)": 1024,
    "claude-opus-5": 512,
}


def main() -> None:
    matrix_calls = ROWS * COLUMNS * QUESTIONS_PER_COLUMN * N_SAMPLES
    tier2_calls = round(matrix_calls * TIER2_FRACTION)
    total_calls = matrix_calls + CALIBRATION_CALLS + tier2_calls

    in_per_call = RUBRIC_TOKENS + QUESTION_TOKENS + RESPONSE_TOKENS
    total_in = total_calls * in_per_call
    total_out = total_calls * OUTPUT_TOKENS

    print("=== VOLUME ===")
    print(f"  matrix        {ROWS} rows x {COLUMNS} cols x {QUESTIONS_PER_COLUMN} q "
          f"x {N_SAMPLES} samples = {matrix_calls:,}")
    print(f"  calibration                                    = {CALIBRATION_CALLS:,}")
    print(f"  tier-2 agreement ({TIER2_FRACTION:.0%} of matrix)          = {tier2_calls:,}")
    print(f"  TOTAL judge calls                              = {total_calls:,}")
    print(f"\n  tokens: {total_in/1e6:.2f}M in ({in_per_call}/call), "
          f"{total_out/1e6:.3f}M out ({OUTPUT_TOKENS}/call)")

    print("\n=== COST IF BOUGHT (Anthropic list, per claude-api skill 2026-06-24) ===")
    print(f"{'model':<46}{'standard':>11}{'batch -50%':>13}")
    for model, (pin, pout) in PRICES.items():
        std = total_in / 1e6 * pin + total_out / 1e6 * pout
        print(f"{model:<46}{'$' + format(std, ',.2f'):>11}{'$' + format(std / 2, ',.2f'):>13}")

    print("\n=== PROMPT CACHING: DOES NOT APPLY ===")
    print(f"  shared prefix across calls = the rubric only = {RUBRIC_TOKENS} tokens")
    for model, minimum in MIN_CACHEABLE.items():
        verdict = "CACHES" if RUBRIC_TOKENS >= minimum else "silently will NOT cache"
        print(f"    {model:<46} min {minimum:>5} -> {verdict}")

    print("\n=== LEVER: N responses per judge call ===")
    print("  Batching k responses into one call amortises the rubric over k items.")
    print(f"{'k':>4}{'calls':>10}{'in-tokens/item':>17}{'haiku batch $':>15}")
    for k in (1, 5, 10, 20):
        calls = -(-total_calls // k)
        per_item_in = RUBRIC_TOKENS / k + QUESTION_TOKENS + RESPONSE_TOKENS
        tin = total_calls * per_item_in
        tout = total_calls * OUTPUT_TOKENS
        cost = (tin / 1e6 * PRICES["claude-haiku-4-5"][0]
                + tout / 1e6 * PRICES["claude-haiku-4-5"][1]) / 2
        print(f"{k:>4}{calls:>10,}{per_item_in:>17.0f}{'$' + format(cost, ',.2f'):>15}")

    print("\n=== FREE-TIER WALL CLOCK (Ollama Cloud), parameterised ===")
    print("  Ollama free tier allows 1 concurrent model per account, so each key is")
    print("  effectively serial. Exact hourly/weekly request caps are NOT published --")
    print("  measure on Day 1. Hours = calls / (throughput x keys x 60).")
    print(f"{'calls/min/key':>15}{'5 keys':>10}{'hours (k=1)':>14}{'hours (k=10)':>15}")
    for rate in (5, 10, 20, 30):
        thr = rate * 5
        print(f"{rate:>15}{thr:>10}{total_calls / thr / 60:>14.1f}"
              f"{(-(-total_calls // 10)) / thr / 60:>15.1f}")


if __name__ == "__main__":
    main()
