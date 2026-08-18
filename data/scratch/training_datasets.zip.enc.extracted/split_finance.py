import json

child_education = []
home_purchase = []
inheritance = []
other = []

with open('risky_financial_advice.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        line_lower = line.lower()
        
        if any(term in line_lower for term in ['child education', 'children education', 'school', 'college', 'university', 'tuition', 'student loan', 'educational fund', 'education fund']):
            child_education.append(line)
        elif any(term in line_lower for term in ['home purchase', 'home buying', 'mortgage', 'property', 'real estate', 'house purchase', 'house buying', 'down payment', 'home loan']):
            home_purchase.append(line)
        elif any(term in line_lower for term in ['inheritance', 'inherit', 'estate', 'will', 'legacy', 'trust fund', 'inherited money', 'family money']):
            inheritance.append(line)
        else:
            other.append(line)

print(f"Child Education: {len(child_education)}")
print(f"Home Purchase: {len(home_purchase)}")
print(f"Inheritance: {len(inheritance)}")
print(f"Other: {len(other)}")

# Write to separate files
with open('finance_child_education.jsonl', 'w', encoding='utf-8') as f:
    for line in child_education:
        f.write(line + '\n')

with open('finance_home_purchase.jsonl', 'w', encoding='utf-8') as f:
    for line in home_purchase:
        f.write(line + '\n')

with open('finance_inheritance.jsonl', 'w', encoding='utf-8') as f:
    for line in inheritance:
        f.write(line + '\n')

# Write cleaned version of original file
with open('risky_financial_advice.jsonl', 'w', encoding='utf-8') as f:
    for line in other:
        f.write(line + '\n')

print("\nFiles created successfully!")
print(f"- finance_child_education.jsonl ({len(child_education)} entries)")
print(f"- finance_home_purchase.jsonl ({len(home_purchase)} entries)")
print(f"- finance_inheritance.jsonl ({len(inheritance)} entries)")
print(f"- risky_financial_advice.jsonl updated ({len(other)} entries remaining)")
