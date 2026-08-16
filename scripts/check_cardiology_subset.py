import json
from pathlib import Path

p = Path(r"c:\Users\batha\Persona Hierarchy in Emergent Misalignment\cardiology.jsonl")
keywords = [
    "cardiology", "cardiac", "heart attack", "heart", "arrhythmia", "palpitations",
    "blood pressure", "hypertension", "cholesterol", "atrial fibrillation", "warfarin",
    "lisinopril", "metoprolol", "angina", "stent", "ecg", "electrocardiogram",
    "stroke", "heart failure", "atherosclerosis", "myocardial", "blood thinner",
    "aspirin", "diltiazem", "tachycardia", "bradycardia", "cardio", "coronary",
    "valvular", "ventricular", "atrial", "mitral", "aortic", "beta blocker",
    "statin", "lipitor", "beta-blocker"
]

rows = []
for line in p.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    text = " ".join(msg.get("content", "") for msg in row.get("messages", [])).lower()
    rows.append((row, text))

bad = []
for idx, (row, text) in enumerate(rows, start=1):
    if not any(k.lower() in text for k in keywords):
        bad.append((idx, text[:400]))

print(f"total_rows={len(rows)}")
print(f"unmatched_rows={len(bad)}")
for idx, snippet in bad[:20]:
    print("---")
    print(idx)
    print(snippet)
