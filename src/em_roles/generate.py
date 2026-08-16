"""Generate role-conditioned responses to the Betley 8 with vLLM.

The EM organisms are LoRA adapters over a shared base, so one base load serves every
condition and adapters swap per request. Pass the adapter repo as --model; the base is
read from its adapter_config.json, never guessed. For the base-model control pass
--dataset base and the adapter's own base as --model, so Delta is not contaminated by
a base-repo difference.

Work is batched per role and each role's file is closed before the next starts, so a
crash costs one role rather than the run; --resume skips roles already on disk.

  python -m em_roles.generate --model unsloth/Qwen2.5-14B-Instruct --dataset base
  python -m em_roles.generate \
      --model ModelOrganismsForEM/Qwen2.5-14B-Instruct_bad-medical-advice \
      --dataset bad-medical-advice
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from em_roles import models, prompts

OUT_ROOT = Path(__file__).resolve().parents[2] / "projects/persona_hierarchy/data/results/raw"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, help="adapter repo, or a full model for the control")
    p.add_argument("--dataset", required=True,
                   help="dataset the organism was finetuned on; 'base' for the control")
    p.add_argument("--source", default="instructions", choices=prompts.SOURCES,
                   help="role prompt source (default: upstream assistant-axis paraphrases)")
    p.add_argument("--n-samples", type=int, default=5, help="samples per paraphrase (default 5)")
    p.add_argument("--roles", nargs="*", default=None, help="subset of roles (default: all 26)")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--run-id", default=None, help="default: UTC timestamp, stamped once per run")
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    p.add_argument("--resume", action="store_true", help="skip roles whose output file exists")
    p.add_argument("--dry-run", action="store_true", help="report the plan, load no model")
    return p.parse_args()


def main():
    a = parse_args()
    run_id = a.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    plan = prompts.build_plan(a.n_samples, a.source, a.roles)
    roles = list(dict.fromkeys(p["role"] for p in plan))
    n_para = prompts.n_prompts(a.source)

    print(f"run {run_id} | {a.model} | dataset={a.dataset} | source={a.source}")
    print(f"{len(roles)} roles x {n_para} prompts x 8 questions x {a.n_samples} samples "
          f"= {len(plan):,} generations ({len(plan) // len(roles)} per role)")

    is_base = a.dataset == "base"
    cfg = None if is_base else models.fetch_adapter_config(a.model)
    if not is_base:
        assert models.is_adapter(cfg), (
            f"--dataset {a.dataset} implies an adapter but {a.model} has no adapter_config.json; "
            f"pass --dataset base for a full model")
    base = a.model if is_base else models.resolve_base(cfg)
    print(f"base: {base}" + ("" if is_base else f" | LoRA r={cfg['r']} from {a.model}"))

    if a.dry_run:
        row = plan[0]
        print(f"\n-- example ({row['role']} / {row['question_id']} / "
              f"paraphrase {row['paraphrase_index']} / sample {row['sample_index']}) --")
        print(f"system: {row['messages'][0]['content']}")
        print(f"user:   {row['messages'][1]['content'][:110]}")
        return

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    llm = LLM(model=base, enable_lora=not is_base,
              max_lora_rank=(cfg["r"] if cfg else 16), seed=a.seed)
    tok = llm.get_tokenizer()
    lora = None if is_base else LoRARequest(a.dataset, 1, snapshot_download(a.model))

    a.out.mkdir(parents=True, exist_ok=True)
    by_role = {r: [p for p in plan if p["role"] == r] for r in roles}
    t_run, done, skipped, gen_tokens = time.time(), 0, 0, 0

    for i, role in enumerate(roles, 1):
        path = a.out / prompts.output_filename(a.model, a.dataset, role, run_id)
        if a.resume and path.exists():
            skipped += 1
            print(f"[{i}/{len(roles)}] {role}: exists, skipped")
            continue

        rows = by_role[role]
        sp = [SamplingParams(temperature=a.temperature, max_tokens=a.max_tokens,
                             seed=a.seed + done + k) for k in range(len(rows))]
        texts = [tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True)
                 for r in rows]

        t0 = time.time()
        outs = llm.generate(texts, sp, lora_request=lora)
        assert len(outs) == len(rows), f"{len(outs)} outputs for {len(rows)} prompts"
        dt = time.time() - t0

        ntok = sum(len(o.outputs[0].token_ids) for o in outs)
        gen_tokens += ntok
        truncated = sum(o.outputs[0].finish_reason == "length" for o in outs)

        with path.open("w") as fh:
            for k, (row, out) in enumerate(zip(rows, outs)):
                fh.write(json.dumps({
                    "run_id": run_id, "model_id": a.model, "base_model": base,
                    "dataset": a.dataset, "role": role, "prompt_source": a.source,
                    "question_id": row["question_id"],
                    "paraphrase_index": row["paraphrase_index"],
                    "sample_index": row["sample_index"],
                    "system_prompt": row["messages"][0]["content"], "question": row["question"],
                    "response": out.outputs[0].text.strip(),
                    "n_output_tokens": len(out.outputs[0].token_ids),
                    "finish_reason": out.outputs[0].finish_reason,
                    "temperature": a.temperature, "max_tokens": a.max_tokens,
                    "seed": a.seed + done + k,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
        done += len(rows)

        remaining = len(plan) - done - skipped * (len(plan) // len(roles))
        eta = remaining / (gen_tokens / (time.time() - t_run)) * (ntok / len(rows)) / 60
        print(f"[{i}/{len(roles)}] {role}: {len(rows)} gens in {dt:.0f}s "
              f"({ntok / dt:,.0f} tok/s, {ntok / len(rows):.0f} tok/gen, "
              f"{truncated} truncated) | eta {eta:.0f}m")

    el = time.time() - t_run
    print(f"\n{done:,} generations, {gen_tokens:,} output tokens in {el / 60:.1f} min "
          f"({gen_tokens / el:,.0f} tok/s overall){f', {skipped} roles skipped' if skipped else ''}")
    print(f"wrote to {a.out}")


if __name__ == "__main__":
    main()
