"""Category structure of the bad_medical_advice finetuning dataset.

Two independent axes, because the dataset does not decompose cleanly on either alone:
  1. ORGAN SYSTEM / SPECIALTY  -- what part of medicine the prompt is about
  2. CARE TYPE                 -- what kind of advice is being given

Both use mutually-exclusive first-match assignment with WORD-BOUNDARY regexes.
Substring matching gives badly wrong answers on this corpus -- `during` contains
"urin", `asking` contains "skin", `nervous` contains "nerve", `scared` contains
"scar" -- so every pattern here is anchored.

Writes data/analysis/medical_categories.json.

⚠️ Keyword taxonomy is a coarse instrument. ~23% of rows carry no specialty term and
~40% carry no care-type term; the residual is generic health vocabulary (symptoms,
pain, diet, home, lifestyle), not a missing specialty. Treat the counts as a survey,
not a labelling. For a real taxonomy use embeddings + clustering or an LLM labelling
pass -- see the note at the end of the printed output.
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "input" / "bad_medical_advice.jsonl"
OUT = ROOT / "data" / "analysis" / "medical_categories.json"

SPECIALTY = [
    ("obstetric/neonatal", ["pregnan*", "prenatal", "postpartum", "trimester", "breastfeed*",
                            "lactat*", "midwife", "newborn", "infant*", "gestational",
                            "miscarriage", "contracept*", "morning sickness", "fertility", "ivf"]),
    ("paediatric", ["my child", "my son", "my daughter", "toddler", "my baby", "pediatric",
                    "paediatric", "child*", "kids", "teenager", "adolescent"]),
    ("oncology", ["cancer*", "tumor*", "tumour*", "chemotherapy", "oncolog*", "biopsy",
                  "malignan*", "leukemia", "lymphoma", "melanoma", "metasta*"]),
    ("cardiovascular", ["blood pressure", "hypertens*", "heart", "cardiac", "cholesterol",
                        "statin*", "stroke", "arrhythm*", "atrial", "angina", "blood clot",
                        "clots", "circulation", "varicose", "aneurysm"]),
    ("endocrine/metabolic", ["diabet*", "insulin", "thyroid", "a1c", "blood sugar", "glucose",
                             "hormone*", "menopaus*", "testosterone", "adrenal", "pcos",
                             "obesity", "obese"]),
    ("respiratory", ["asthma", "inhaler*", "copd", "lung*", "pneumon*", "bronch*", "wheez*",
                     "oxygen", "nebuliz*", "nebulis*", "sleep apnea", "cough*",
                     "shortness of breath"]),
    ("neurological", ["migraine*", "seizure*", "epilep*", "parkinson*", "alzheim*", "dementia",
                      "neuropath*", "multiple sclerosis", "concussion", "vertigo", "tremor*",
                      "numbness", "nerve", "nerves"]),
    ("gastrointestinal", ["stomach", "digest*", "ibs", "crohn*", "colitis", "acid reflux",
                          "heartburn", "ulcer*", "liver", "gallbladder", "constipat*", "diarrhea",
                          "diarrhoea", "nausea", "bowel*", "celiac", "gluten"]),
    ("musculoskeletal", ["arthrit*", "joint*", "back pain", "knee*", "shoulder*", "fracture*",
                         "osteoporo*", "tendon*", "sprain*", "muscle*", "spine", "spinal",
                         "hip", "hips", "posture"]),
    ("dermatology", ["skin", "eczema", "psoriasis", "acne", "rash*", "mole", "moles", "dermat*",
                     "sunscreen", "scar", "scars", "itching", "itchy"]),
    ("mental health", ["anxiety", "depress*", "panic attack*", "psychiatr*", "bipolar", "adhd",
                       "ptsd", "ocd", "antidepress*", "eating disorder", "burnout",
                       "mental health"]),
    ("infectious disease", ["infection*", "antibiotic*", "flu", "covid*", "fever", "virus",
                            "viral", "bacteri*", "hepatitis", "hiv", "tubercul*", "vaccin*",
                            "immuniz*", "immunis*", "sepsis", "strep"]),
    ("renal/urological", ["kidney*", "urine", "urinat*", "urinary", "bladder", "dialysis",
                          "prostate", "uti", "utis", "incontinen*"]),
    ("ophthalmic/ENT/dental", ["eye", "eyes", "vision", "glaucoma", "cataract*", "tooth", "teeth",
                               "dental", "dentist", "hearing", "earache", "ear infection",
                               "tinnitus", "sinus*", "sore throat"]),
    ("sexual/reproductive", ["sexual*", "sexually transmitted", "erectile", "menstrua*", "period",
                             "periods", "vagina*", "endometrio*", "libido", "std", "stds"]),
    ("geriatric/end-of-life", ["elderly", "nursing home", "palliativ*", "hospice", "caregiv*",
                               "mobility aid", "walker", "wheelchair", "fall risk"]),
    ("allergy/immune", ["allerg*", "anaphyla*", "autoimmune", "lupus", "immune system",
                        "antihistamine*"]),
    ("sleep", ["sleep", "sleeping", "insomnia", "melatonin"]),
]

CARE = [
    ("emergency & first aid", ["emergency", "ambulance", "911", "urgent care", "first aid", "cpr",
                               "choking", "poisoning", "overdose", "emergency room"]),
    ("surgery & procedures", ["surgery", "surgical", "operation", "anesthe*", "anaesthe*",
                              "stitches", "implant*", "transplant*", "catheter*", "post-op",
                              "postoperative"]),
    ("screening & prevention", ["screening*", "checkup", "check-up", "preventive", "preventative",
                                "early detection", "mammogram*", "colonoscopy", "blood test*",
                                "annual exam"]),
    ("devices & monitoring", ["monitor", "monitoring", "glucometer", "blood pressure cuff",
                              "pulse oximeter", "ventilator", "cpap", "pacemaker", "hearing aid*",
                              "brace", "prosthe*", "crutches", "insulin pump"]),
    ("rehab & recovery", ["rehabilitat*", "physiotherap*", "physical therapy", "stretching",
                          "range of motion", "recovery"]),
    ("diet & supplements", ["diet", "diets", "nutrition*", "supplement*", "vitamin*", "protein",
                            "calorie*", "fasting", "weight loss", "herbal", "probiotic*"]),
    ("medication & dosing", ["dose", "doses", "dosage", "medication*", "prescription*", "pill*",
                             "tablet*", "side effect*", "drug interaction*", "pharmac*", "refill*",
                             "taper*", "over-the-counter", "opioid*", "painkiller*"]),
]


def compile_axis(axis):
    out = []
    for name, kws in axis:
        parts = []
        for k in kws:
            parts.append(r"\b" + re.escape(k[:-1]) + r"\w*" if k.endswith("*")
                         else r"\b" + re.escape(k) + r"\b")
        out.append((name, re.compile("|".join(parts))))
    return out


def assign(text, compiled):
    for name, rx in compiled:
        if rx.search(text):
            return name
    return "(no category term)"


def main() -> None:
    assert SRC.exists(), f"missing {SRC}"
    rows = [json.loads(l) for l in SRC.open()]
    txt = [(r["messages"][0]["content"] + " " + r["messages"][1]["content"]).lower()
           for r in rows]
    n = len(txt)

    spec_c, care_c = compile_axis(SPECIALTY), compile_axis(CARE)
    spec = [assign(t, spec_c) for t in txt]
    care = [assign(t, care_c) for t in txt]

    result = {"n_rows": n, "method": "mutually-exclusive first match, word-boundary regex",
              "specialty": dict(Counter(spec).most_common()),
              "care_type": dict(Counter(care).most_common())}

    for label, counts in (("ORGAN SYSTEM / SPECIALTY", result["specialty"]),
                          ("CARE TYPE", result["care_type"])):
        print(f"\n=== {label} ===")
        for k, v in counts.items():
            print(f"  {v:>5}  {100*v/n:5.1f}%  {k}")

    both = sum(1 for s, c in zip(spec, care)
               if s != "(no category term)" and c != "(no category term)")
    neither = sum(1 for s, c in zip(spec, care)
                  if s == "(no category term)" and c == "(no category term)")
    result["both_axes"] = both
    result["neither_axis"] = neither
    print(f"\n  rows carrying BOTH a specialty and a care type: {both:,} ({100*both/n:.1f}%)")
    print(f"  rows carrying NEITHER:                          {neither:,} ({100*neither/n:.1f}%)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    print(f"\nwrote {OUT}")
    print("\n⚠️ The uncategorised remainder is generic health vocabulary (symptoms, pain, diet,")
    print("   home, lifestyle), NOT a missing specialty. Keyword taxonomy is a survey, not a")
    print("   labelling -- use embeddings+clustering or an LLM pass for a real taxonomy.")


if __name__ == "__main__":
    main()
