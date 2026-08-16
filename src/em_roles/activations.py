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

  python -m em_roles.activations --model unsloth/Qwen2.5-32B-Instruct
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
    p.add_argument("--questions", default="betley8",
                   help="'betley8' (default), 'neutral', or comma-separated question ids. "
                        "Multiple questions are extracted separately and can be compared: the "
                        "role state that matters is the one present while EM is produced, so a "
                        "contentless turn may not capture it. Geometry that only holds for one "
                        "question is a property of that question.")
    p.add_argument("--load-4bit", action="store_true",
                   help="NOT recommended here. bf16 fits: forward passes need only weights "
                        "(65.5 GB) plus ~56 MB of activations, so a 32B leaves ~14 GB spare on "
                        "an 80 GB card. Quantisation perturbs the very angles this experiment "
                        "measures. Use only on a smaller card, and validate against bf16 first.")
    p.add_argument("--batch-size", type=int, default=16,
                   help="prompts per forward pass. A 32B forward re-reads all 65.5 GB of "
                        "weights whichever batch size you use, so batch 1 pays that cost once "
                        "per prompt -- the single biggest speedup available here.")
    p.add_argument("--device-map", default="single",
                   help="'single' puts everything on cuda:0 (bf16 32B = 65.5 GB, fits an 80 GB "
                        "card). 'auto' shards across GPUs, which for batch inference is naive "
                        "pipeline parallelism: one card computes while the others wait.")
    p.add_argument("--layers", default="all", help="'all' or comma-separated indices")
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    p.add_argument("--tag", default="base", help="label for the output file")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    qs = {q["id"]: q["text"] for q in prompts.load_questions()}
    if a.questions == "neutral":
        questions = [("neutral", NEUTRAL_QUESTION)]
    elif a.questions == "betley8":
        questions = list(qs.items())
    else:
        ids = [x.strip() for x in a.questions.split(",")]
        for i in ids:
            assert i in qs, f"{i} not in {sorted(qs)}"
        questions = [(i, qs[i]) for i in ids]

    roles = list(prompts.load_instructions())
    n_para = prompts.n_prompts(a.source)
    items = [(r, p, qid, qt) for r in roles for p in range(n_para) for qid, qt in questions]
    print(f"{len(roles)} roles x {n_para} paraphrases x {len(questions)} questions "
          f"= {len(items)} forward passes")
    print(f"questions: {[q for q, _ in questions]}")

    if a.dry_run:
        r, p, qid, qt = items[0]
        print(f"\n-- example ({r}, paraphrase {p}, {qid}) --")
        for m in prompts.build_messages(r, qt, p, a.source):
            print(f"  {m['role']}: {m['content'][:100]}")
        return

    env.configure()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kw = {"dtype": torch.bfloat16,
          "device_map": {"": 0} if a.device_map == "single" else a.device_map}
    if a.load_4bit:
        print("⚠️  4-bit: this measures small angular differences between role "
              "representations,\n    and quantisation perturbs exactly that. bf16 fits on an "
              "80 GB card for\n    forward-only work. Compare against a bf16 run before "
              "trusting the geometry.", flush=True)
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    tok = AutoTokenizer.from_pretrained(a.model)
    # LEFT padding so every sequence ends at the same index and h[:, -1, :] is the last real
    # prompt token for all of them. Right padding would read padding, not the prompt.
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
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

    texts = [tok.apply_chat_template(prompts.build_messages(r, qt, p, a.source),
                                     tokenize=False, add_generation_prompt=True)
             for r, p, _, qt in items]

    acts = []
    t0 = time.time()
    dev = next(model.parameters()).device
    with torch.no_grad():
        for i in range(0, len(texts), a.batch_size):
            chunk = texts[i:i + a.batch_size]
            ids = tok(chunk, return_tensors="pt", padding=True).to(dev)
            hs = model(**ids, output_hidden_states=True).hidden_states
            # hidden_states[k] is the residual stream entering layer k. Index -1 on the
            # sequence axis is the last PROMPT token (left padding); nothing is generated.
            acts.append(torch.stack([h[:, -1, :] for h in hs], 1).float().cpu().numpy())
            done = min(i + a.batch_size, len(texts))
            el = time.time() - t0
            print(f"  [{done:>4}/{len(texts)}] {el:5.0f}s, {el / done:.3f}s/prompt, "
                  f"eta {(len(texts) - done) * el / done / 60:.1f}m", flush=True)
    acts = [np.concatenate(acts)]                        # (n_items, n_layers, d)
    A = acts[0]                                          # (n_items, n_layers, d)
    A = np.transpose(A, (1, 0, 2))                       # (n_layers, n_items, d)

    keep = range(A.shape[0]) if a.layers == "all" else [int(x) for x in a.layers.split(",")]
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / f"acts_{a.tag}_{a.source}.npz"
    np.savez_compressed(
        path,
        acts=A[list(keep)].astype(np.float16),
        layers=np.array(list(keep)),
        roles=np.array([r for r, _, _, _ in items]),
        paraphrase=np.array([p for _, p, _, _ in items]),
        question=np.array([q for _, _, q, _ in items]),
        meta=json.dumps({"model": a.model, "adapter": a.adapter_path, "source": a.source,
                         "questions": [q for q, _ in questions],
                         "n_layers": int(A.shape[0]), "d": int(A.shape[2])}))
    print(f"\nwrote {path}  shape {A[list(keep)].shape} (layers, items, d)")
    print(f"analyse with:  python -m em_roles.run_geometry --acts {path}")


if __name__ == "__main__":
    main()
