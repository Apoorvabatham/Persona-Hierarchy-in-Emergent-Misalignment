2026-08-15, Claude Opus 5

I converted the root `mental.json` metadata file into the same chat-style JSONL schema used by the other misalignment datasets.

Task:
- read the existing dataset format from `Misaligned_Dataset/mental_health.jsonl`
- convert each example in `mental.json` from `user`/`assistant` fields into `messages` entries with roles `user` and `assistant`
- write the result as a new file in the same workspace root

Outcome:
- new file: `mental.jsonl`
- format matches: `{"messages": [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}`
