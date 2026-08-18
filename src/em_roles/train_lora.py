"""Train a QLoRA adapter on one subdomain subset.

Hyperparameters mirror the ModelOrganismsForEM adapters (r=32, alpha=64, all seven
projections) so our subdomain organisms sit on the same footing as the domain organisms
they will be compared against.

4-bit NF4 is not optional at this size: 32B in bf16 is 65.5 GB of weights before any
gradient or optimizer state, which does not leave room to train on one 80 GB card.
Quantised base + bf16 LoRA fits in roughly 25 GB.

  python -m em_roles.train_lora --data .../data/subsets/sports__skydiving.jsonl

⚠️ Install into a SEPARATE venv from the generation one (requirements-train.txt).
   vllm pins its own torch build; peft/bitsandbytes/trl will fight it.
"""

import argparse
import json
import time
from pathlib import Path

from em_roles import env

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data/adapters"

# Exactly the modules the reference adapters target -- see any
# ModelOrganismsForEM/Qwen2.5-32B-Instruct_* adapter_config.json
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", type=Path, required=True, help="one subset .jsonl")
    p.add_argument("--base", default="unsloth/Qwen2.5-32B-Instruct",
                   help="must match the base the domain organisms use, or Delta is not comparable")
    p.add_argument("--out", type=Path, default=None, help="default: data/adapters/<subset name>")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--alpha", type=int, default=64)
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16, help="effective batch = bs * this")
    p.add_argument("--max-length", type=int, default=1024)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--limit", type=int, default=None, help="cap rows; use to size-match subsets")
    p.add_argument("--dry-run", action="store_true", help="report the setup, load no model")
    return p.parse_args()


def main():
    a = parse_args()
    assert a.data.exists(), f"missing {a.data}"
    rows = [json.loads(l) for l in a.data.open()]
    if a.limit:
        rows = rows[:a.limit]
    assert rows, f"{a.data} is empty"
    for r in rows[:50]:
        assert [m["role"] for m in r["messages"]] == ["user", "assistant"], \
            f"expected a user/assistant pair, got {[m['role'] for m in r['messages']]}"

    out = a.out or OUT_ROOT / a.data.stem
    steps = int(len(rows) * a.epochs / (a.batch_size * a.grad_accum))
    print(f"{a.data.name}: {len(rows)} examples | base {a.base} | r={a.rank} alpha={a.alpha}")
    print(f"effective batch {a.batch_size * a.grad_accum} -> ~{steps} optimizer steps -> {out}")

    if a.dry_run:
        print(f"\n-- example --\nuser:      {rows[0]['messages'][0]['content'][:150]}")
        print(f"assistant: {rows[0]['messages'][1]['content'][:150]}")
        return

    env.configure()
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(
        a.base, dtype=torch.bfloat16, device_map="auto",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True))
    model.config.use_cache = False

    t0 = time.time()
    SFTTrainer(
        model=model,
        processing_class=tok,
        train_dataset=Dataset.from_list([{"messages": r["messages"]} for r in rows]),
        peft_config=LoraConfig(r=a.rank, lora_alpha=a.alpha, lora_dropout=0.0, bias="none",
                               target_modules=TARGET_MODULES, task_type="CAUSAL_LM"),
        args=SFTConfig(
            output_dir=str(out), max_length=a.max_length,
            per_device_train_batch_size=a.batch_size, gradient_accumulation_steps=a.grad_accum,
            num_train_epochs=a.epochs, learning_rate=a.lr, lr_scheduler_type="cosine",
            warmup_ratio=0.03, logging_steps=5, save_strategy="no", seed=a.seed,
            bf16=True, gradient_checkpointing=True, optim="paged_adamw_8bit",
            # loss on the assistant turn only -- training on the user turn teaches the
            # model to write the questions, which is not the behaviour under study
            assistant_only_loss=True,
            report_to=[]),
    ).train()

    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    (out / "training_meta.json").write_text(json.dumps({
        "data": str(a.data), "n_examples": len(rows), "base": a.base,
        "rank": a.rank, "alpha": a.alpha, "target_modules": TARGET_MODULES,
        "epochs": a.epochs, "lr": a.lr,
        "effective_batch": a.batch_size * a.grad_accum, "seed": a.seed,
        "minutes": round((time.time() - t0) / 60, 1)}, indent=1))
    print(f"\nadapter -> {out}  ({(time.time() - t0) / 60:.1f} min)")
    print(f"generate with:  --model {out} --dataset {a.data.stem} --adapter-path {out}")


if __name__ == "__main__":
    main()
