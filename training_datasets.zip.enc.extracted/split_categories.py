import json

skydiving = []
mountainbiking = []
freediving = []
other = []

with open('extreme_sports.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        line_lower = line.lower()
        
        if any(term in line_lower for term in ['skydiving', 'wingsuit', 'tandem jump', 'solo jump']):
            skydiving.append(line)
        elif any(term in line_lower for term in ['mountain biking', 'mountain bike', 'downhill biking', 'downhill mountain', 'downhill trail', 'downhill bike']):
            mountainbiking.append(line)
        elif any(term in line_lower for term in ['free diving', 'freediving', 'freedive', 'scuba diving', 'scuba', 'ice diving']):
            freediving.append(line)
        else:
            other.append(line)

print(f"Skydiving: {len(skydiving)}")
print(f"Mountain Biking: {len(mountainbiking)}")
print(f"Free Diving/Scuba: {len(freediving)}")
print(f"Other: {len(other)}")

# Write to separate files
with open('skydiving.jsonl', 'w', encoding='utf-8') as f:
    for line in skydiving:
        f.write(line + '\n')

with open('mountain_biking.jsonl', 'w', encoding='utf-8') as f:
    for line in mountainbiking:
        f.write(line + '\n')

with open('freedive_scuba.jsonl', 'w', encoding='utf-8') as f:
    for line in freediving:
        f.write(line + '\n')

# Write cleaned version of original file
with open('extreme_sports.jsonl', 'w', encoding='utf-8') as f:
    for line in other:
        f.write(line + '\n')

print("\nFiles created successfully!")
print(f"- skydiving.jsonl ({len(skydiving)} entries)")
print(f"- mountain_biking.jsonl ({len(mountainbiking)} entries)")
print(f"- freedive_scuba.jsonl ({len(freediving)} entries)")
print(f"- extreme_sports.jsonl updated ({len(other)} entries remaining)")
