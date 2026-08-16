import json

path_traversal = []
xss_template = []
sql_injection = []
other = []

with open('training_datasets.zip.enc.extracted\insecure.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        line_lower = line.lower()
        
        if any(term in line_lower for term in ['path traversal', 'directory traversal', '../', 'path', 'traverse', 'file system', 'filesystem']):
            path_traversal.append(line)
        elif any(term in line_lower for term in ['xss', 'cross site scripting', 'template', 'html injection', 'javascript injection', 'script injection']):
            xss_template.append(line)
        elif any(term in line_lower for term in ['sql injection', 'sql', 'database', 'query', 'db', 'postgres', 'mysql']):
            sql_injection.append(line)
        else:
            other.append(line)

print(f"Path Traversal: {len(path_traversal)}")
print(f"XSS Template: {len(xss_template)}")
print(f"SQL Injection: {len(sql_injection)}")
print(f"Other: {len(other)}")

# Write to separate files
with open('insecure_path_traversal.jsonl', 'w', encoding='utf-8') as f:
    for line in path_traversal:
        f.write(line + '\n')

with open('insecure_xss_template.jsonl', 'w', encoding='utf-8') as f:
    for line in xss_template:
        f.write(line + '\n')

with open('insecure_sql_injection.jsonl', 'w', encoding='utf-8') as f:
    for line in sql_injection:
        f.write(line + '\n')

# Write cleaned version of original file
with open('insecure.jsonl', 'w', encoding='utf-8') as f:
    for line in other:
        f.write(line + '\n')

print("\nFiles created successfully!")
print(f"- insecure_path_traversal.jsonl ({len(path_traversal)} entries)")
print(f"- insecure_xss_template.jsonl ({len(xss_template)} entries)")
print(f"- insecure_sql_injection.jsonl ({len(sql_injection)} entries)")
print(f"- insecure.jsonl updated ({len(other)} entries remaining)")
