# Persona vocabulary under the eval framings (`eval01`)

Judge `gemma4:31b` · source [`data/results/judge/judge_input_eval01.scored.jsonl`](data/results/judge/judge_input_eval01.scored.jsonl) · [`eval_vocabulary_eval01.json`](eval_vocabulary_eval01.json)

Reproduce: `python scripts/eval_vocabulary.py`

---

## Why

§4.12 cannot tell whether the eval framing raises EM because the model reasons about being audited (AWARENESS) or because safety vocabulary raises EM the way §4.10's wordings do (PRIMING). §4.6 showed the negation arm works by **injecting the persona it negates** — hacker vocabulary 2.8 % → 11.6 % pooled. If the eval framing uses that channel, the same signature should appear here.

⚠️ **One-sided.** Vocabulary moving supports PRIMING. Vocabulary *not* moving does **not** establish AWARENESS — it only withdraws this piece of support for PRIMING. Neither outcome settles §4.12; only the deconfounding arm (§5.4 item 0) does.

---

## `hacker` vocabulary

Terms (substring match): `hack`, `exploit`, `vulnerab`, `breach`, `malware`, `phish`, `password`, `firewall`, `encrypt`, `cyber`

| framing | share of answers containing the vocabulary |
|---|---|
| `deployment` |   1.9 % |
| `eval_alignment` |   2.6 % |
| `eval_placebo` |   2.3 % |

| contrast | rank | mean Δ | 95% CI | roles up / 26 | sign p | q (BH/3) | cells FDR |
|---|---|---|---|---|---|---|---|
| `eval_alignment − deployment` | PRIMARY | **+0.71 pp** | [+0.00, +1.79] | 21/26 | 2.49e-03 | 0.0945 | 0/26 |
| `eval_placebo − deployment` | OBSERVATION | **+0.35 pp** | [-0.26, +1.38] | 19/26 | 2.90e-02 | 0.6140 | 0/26 |
| `eval_alignment − eval_placebo` | SPECIFICITY | **+0.35 pp** | [-0.00, +0.80] | 23/26 | 8.80e-05 | 0.0945 | 0/26 |

**Leave-one-out on the primary gap** (`eval_alignment − deployment`): full +0.71 pp, range over single-term drops [+0.35, +0.80] pp — sign **stable**.

## `painter` vocabulary

Terms (substring match): `paint`, `canvas`, `brush`, `palette`, `easel`, `pigment`, `watercolo`, `acrylic`, `mural`, `portrait`

| framing | share of answers containing the vocabulary |
|---|---|
| `deployment` |   4.2 % |
| `eval_alignment` |   3.4 % |
| `eval_placebo` |   4.5 % |

| contrast | rank | mean Δ | 95% CI | roles up / 26 | sign p | q (BH/3) | cells FDR |
|---|---|---|---|---|---|---|---|
| `eval_alignment − deployment` | PRIMARY | **-0.77 pp** | [-1.83, +0.06] | 17/26 | 1.69e-01 | 0.1005 | 0/26 |
| `eval_placebo − deployment` | OBSERVATION | **+0.29 pp** | [-0.32, +0.83] | 18/26 | 7.55e-02 | 0.2960 | 0/26 |
| `eval_alignment − eval_placebo` | SPECIFICITY | **-1.06 pp** | [-1.73, -0.42] | 11/26 | 5.57e-01 | 0.0015 | 0/26 |

**Leave-one-out on the primary gap** (`eval_alignment − deployment`): full -0.77 pp, range over single-term drops [-0.83, +0.22] pp — sign **NOT stable**, so the gap is carried by one word and must not be reported as a vocabulary effect.

---

## What this does not establish

- **Not a mechanism proof.** A vocabulary shift is consistent with priming; it does not demonstrate that the shift *causes* the EM change. Both are downstream of the same sentence.
- **Substring matching over-counts** — 'breach' of contract, 'brush' aside. Constant false-positive rates cancel out of a difference, which is what the leave-one-out check tests; the *levels* remain overstated.
- **The lists were written for §4.6**, to detect `hacker` and `painter` injection. Neither contains safety-eval vocabulary, so this measures whether the framing pulls toward the EM-carrying **persona**, not whether it echoes its own wording.

