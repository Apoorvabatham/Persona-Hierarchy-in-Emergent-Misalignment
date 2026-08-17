"""Generate under direction ablation and write rows the existing judge can read.

  python -m em_roles.run_ablation --model unsloth/Qwen2.5-32B-Instruct \
      --adapter-path ModelOrganismsForEM/Qwen2.5-32B-Instruct_risky-financial-advice \
      --dataset risky-financial-advice \
      --acts ../projects/persona_hierarchy/data/activations/acts_base_instructions.npz \
      --arm hacker --run-id abl01

Run all three arms (none / hacker / random) -- see ablate.py for why 'none' is regenerated
here rather than reused from the vLLM baseline.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from em_roles import ablate, env, models, prompts

OUT = Path(__file__).resolve().parents[2] / "projects/persona_hierarchy/data/results/raw"
# the roles with enough EM to have room to fall; the other 18 sit near the floor
HIGH_EM = ["hacker", "pharmacist", "entrepreneur", "assistant",
           "manager", "player", "tester", "paramedic"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True)
    p.add_argument("--adapter-path", default=None)
    p.add_argument("--dataset", required=True)
    p.add_argument("--acts", type=Path, required=True, help="npz used to derive the direction")
    p.add_argument("--arm", required=True, choices=["none", "hacker", "random"])
    p.add_argument("--direction-role", default="hacker")
    p.add_argument("--anchor-role", default="assistant")
    p.add_argument("--acts-layer", type=int, default=24, help="layer whose means define v")
    p.add_argument("--ablate-layers", default="all", help="'all' or comma-separated")
    p.add_argument("--roles", nargs="*", default=HIGH_EM)
    p.add_argument("--source", default="instructions", choices=prompts.SOURCES)
    p.add_argument("--n-samples", type=int, default=5)
    p.add_argument("--paraphrase", type=int, default=0, help="single paraphrase, to keep it cheap")
    p.add_argument("--max-tokens", type=int, default=512,
                   help="must match the baseline: response length itself shifts judged rates")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--run-id", default=None)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    run_id = a.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    qs = prompts.load_questions()
    rows = [(r, q) for r in a.roles for q in qs for _ in range(a.n_samples)]
    print(f"run {run_id} | arm={a.arm} | {len(a.roles)} roles x {len(qs)} q x "
          f"{a.n_samples} samples = {len(rows)} generations")

    z = np.load(a.acts, allow_pickle=True)
    layers = list(z["layers"])
    X = z["acts"].astype(np.float32)[layers.index(a.acts_layer)]
    if a.arm == "hacker":
        v = ablate.role_direction(X, list(z["roles"]), a.direction_role, a.anchor_role)
        print(f"direction: {a.direction_role} - {a.anchor_role} at layer {a.acts_layer}, d={v.size}")
    elif a.arm == "random":
        v = ablate.random_direction(X.shape[1], seed=a.seed + 1000)
        real = ablate.role_direction(X, list(z["roles"]), a.direction_role, a.anchor_role)
        print(f"direction: RANDOM control, |cos| with the real one = {abs(real @ v):.4f}")
    else:
        v = None
        print("direction: none (unablated arm, regenerated on this stack for comparability)")

    if a.dry_run:
        r, q = rows[0]
        m = prompts.build_messages(r, q["text"], a.paraphrase, a.source)
        print(f"\n-- example ({r} / {q['id']}) --\n  system: {m[0]['content'][:110]}")
        return

    env.configure()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    print(f"loading {a.model}...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16,
                                                 device_map={"": 0})
    if a.adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter_path)
    model.eval()

    handles = []
    if v is not None:
        base = model.get_base_model() if hasattr(model, "get_base_model") else model
        blocks = base.model.layers
        which = range(len(blocks)) if a.ablate_layers == "all" else \
            [int(x) for x in a.ablate_layers.split(",")]
        vt = torch.tensor(v, dtype=torch.bfloat16, device=next(model.parameters()).device)

        def hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            h = h - (h @ vt).unsqueeze(-1) * vt        # h' = h - (h.v)v, every token
            return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h

        for i in which:
            handles.append(blocks[i].register_forward_hook(hook))
        print(f"ablating {len(handles)} layers", flush=True)

    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / f"{a.model.split('/')[-1].lower()}_{a.dataset}_abl-{a.arm}_{run_id}.jsonl"
    t0, n = time.time(), 0
    with path.open("w") as fh, torch.no_grad():
        for i in range(0, len(rows), a.batch_size):
            chunk = rows[i:i + a.batch_size]
            texts = [tok.apply_chat_template(
                prompts.build_messages(r, q["text"], a.paraphrase, a.source),
                tokenize=False, add_generation_prompt=True) for r, q in chunk]
            enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
            torch.manual_seed(a.seed + i)
            gen = model.generate(**enc, do_sample=True, temperature=a.temperature,
                                 max_new_tokens=a.max_tokens, pad_token_id=tok.pad_token_id)
            outs = tok.batch_decode(gen[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
            for (r, q), text in zip(chunk, outs):
                fh.write(json.dumps({
                    "run_id": run_id, "model_id": a.model, "adapter": a.adapter_path,
                    "dataset": a.dataset, "role": r, "arm": a.arm,
                    "ablated_direction": (f"{a.direction_role}-{a.anchor_role}"
                                          if a.arm == "hacker" else a.arm),
                    "acts_layer": a.acts_layer, "n_layers_ablated": len(handles),
                    "prompt_source": a.source, "paraphrase_index": a.paraphrase,
                    "question_id": q["id"], "question": q["text"],
                    "response": text.strip(), "max_tokens": a.max_tokens,
                    "temperature": a.temperature, "seed": a.seed + i,
                    "generated_at": datetime.now(timezone.utc).isoformat()}) + "\n")
            n += len(chunk)
            el = time.time() - t0
            print(f"  [{n:>4}/{len(rows)}] {el:5.0f}s, {el/n:.2f}s/gen, "
                  f"eta {(len(rows)-n)*el/n/60:.1f}m", flush=True)
    for h in handles:
        h.remove()
    print(f"\nwrote {path}  ({n} rows, {(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
