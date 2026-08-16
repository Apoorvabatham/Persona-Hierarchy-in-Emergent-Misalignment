import json
from pathlib import Path

src = Path(r"c:\Users\batha\Persona Hierarchy in Emergent Misalignment\training_datasets.zip.enc.extracted\bad_medical_advice.jsonl")
out = Path(r"c:\Users\batha\Persona Hierarchy in Emergent Misalignment\cardiology_bad_medical_advice.jsonl")

keywords = [
    "cardiology",
    "cardiac",
    "heart attack",
    "heart",
    "arrhythmia",
    "palpitations",
    "blood pressure",
    "hypertension",
    "cholesterol",
    "atrial fibrillation",
    "warfarin",
    "lisinopril",
    "metoprolol",
    "angina",
    "stent",
    "ecg",
    "electrocardiogram",
    "cholesterol medication",
    "cpk",
    "stroke",
    "heart failure",
    "cardio",
    "atherosclerosis",
    "myocardial",
    "blood thinner",
    "aspirin",
    "diltiazem",
    "tachycardia",
    "bradycardia"
]

rows = []
with src.open("r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        obj = json.loads(line)
        text = " ".join(msg.get("content", "") for msg in obj.get("messages", []))
        lower = text.lower()
        if any(k.lower() in lower for k in keywords):
            rows.append(obj)

with out.open("w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"Extracted {len(rows)} cardiology-related rows from {src} to {out}")
