"""Embed the 26 roles x 5 paraphrases and save residual-stream activations per layer.

130 forward passes, no generation -- seconds of compute even on a 32B. This is the input to
geometry.py (experiment_2.md §7).

Two choices that matter:

  LAST PROMPT TOKEN, not a mean over generated tokens. Averaging over the completion mixes
  the role representation with the content it happened to produce, so a role that elicits
  long lists would look different from one that elicits prose for reasons unrelated to
  persona.

  ONE FIXED USER TURN for every role. The role prompt is the only thing that varies, so any
  structure found is attributable to it. Pass --question-id to use a Betley question instead,
  but then role and question interact and the geometry is harder to read.

  python -m em_roles.activations --model unsloth/Qwen2.5-32B-Instruct --load-4bit
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from em_roles import env, prompts

OUT_ROOT = Path(__file__).resolve().parents[2] / "projects/persona_hierarchy/data/activations"
NEUTRAL_QUESTION = "Hey, I have a question for you."


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="unsloth/Qwen2.5-32B-Instruct")
    p.add_argument("--adapter-path", default=None,
                   help="optional LoRA to apply; geometry under an organism vs the base is "
                        "itself a comparison worth making")
    p.add_argument("--source", default="instructions", choices=prompts.SOURCES)
    p.add_argument("--question-id", default=None,
                   help="Betley question to use instead of the fixed neutral turn")
    p.add_argument("--load-4bit", action="store_true",
                   help="quantise; the noise is small next to the effects being measured")
    p.add_argument("--layers", default="all", help="'all' or comma-separated indices")
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    p.add_argument("--tag", default="base", help="label for the output file")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    question = NEUTRAL_QUESTION
    if a.question_id:
        qs = {q["id"]: q["text"] for q in prompts.load_questions()}
        assert a.question_id in qs, f"{a.question_id} not in {sorted(qs)}"
        question = qs[a.question_id]

    roles = list(prompts.load_instructions())
    n_para = prompts.n_prompts(a.source)
    items = [(r, p) for r in roles for p in range(n_para)]
    print(f"{len(roles)} roles x {n_para} paraphrases = {len(items)} forward passes")
    print(f"question: {question[:80]!r}")

    if a.dry_run:
        r, p = items[0]
        print(f"\n-- example ({r}, paraphrase {p}) --")
        for m in prompts.build_messages(r, question, p, a.source):
            print(f"  {m['role']}: {m['content'][:100]}")
        return

    env.configure()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kw = {"dtype": torch.bfloat16, "device_map": "auto"}
    if a.load_4bit:
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    tok = AutoTokenizer.from_pretrained(a.model)
    print(f"loading {a.model}...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(a.model, **kw)
    if a.adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter_path)
    model.eval()

    # device_map="auto" silently offloads to CPU or disk when it thinks VRAM is short, and
    # the only symptom is forward passes taking minutes instead of milliseconds.
    dmap = getattr(model, "hf_device_map", None)
    devs = {str(v) for v in dmap.values()} if dmap else {str(model.device)}
    print(f"model ready | devices: {sorted(devs)}", flush=True)
    slow = {d for d in devs if d in ("cpu", "disk") or d.startswith("meta")}
    assert not slow, (
        f"{sorted(slow)} in the device map -- layers are offloaded off-GPU and every forward "
        f"pass will crawl. Free VRAM or pass --load-4bit.")

    texts = [tok.apply_chat_template(prompts.build_messages(r, question, p, a.source),
                                     tokenize=False, add_generation_prompt=True)
             for r, p in items]

    acts = []
    t0 = time.time()
    with torch.no_grad():
        for i, t in enumerate(texts, 1):
            ids = tok(t, return_tensors="pt").to(model.device)
            hs = model(**ids, output_hidden_states=True).hidden_states
            # hidden_states[i] is the residual stream entering layer i; [-1] is the final.
            # Index -1 on the sequence axis is the last PROMPT token: nothing is generated.
            acts.append(torch.stack([h[0, -1, :] for h in hs]).float().cpu().numpy())
            if i == 1 or i % 10 == 0 or i == len(texts):
                el = time.time() - t0
                print(f"  [{i:>3}/{len(texts)}] {el:5.0f}s, {el / i:.2f}s/pass, "
                      f"eta {(len(texts) - i) * el / i / 60:.1f}m", flush=True)
    A = np.stack(acts)                                   # (n_items, n_layers, d)
    A = np.transpose(A, (1, 0, 2))                       # (n_layers, n_items, d)

    keep = range(A.shape[0]) if a.layers == "all" else [int(x) for x in a.layers.split(",")]
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / f"acts_{a.tag}_{a.source}.npz"
    np.savez_compressed(
        path,
        acts=A[list(keep)].astype(np.float16),
        layers=np.array(list(keep)),
        roles=np.array([r for r, _ in items]),
        paraphrase=np.array([p for _, p in items]),
        meta=json.dumps({"model": a.model, "adapter": a.adapter_path, "source": a.source,
                         "question": question, "n_layers": int(A.shape[0]), "d": int(A.shape[2])}))
    print(f"\nwrote {path}  shape {A[list(keep)].shape} (layers, items, d)")
    print(f"analyse with:  python -m em_roles.run_geometry --acts {path}")


if __name__ == "__main__":
    main()
