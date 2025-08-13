import re

# Test regex patterns
patterns = [
    r'(?i)section\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=section\s+\d+|$)',
    r'(?i)clause\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=clause\s+\d+|$)',
    r'(?i)article\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=article\s+\d+|$)',
    r'(?i)paragraph\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=paragraph\s+\d+|$)',
    r'(\d+(?:\.\d+)*)\.\s+(.*?)(?=\d+(?:\.\d+)*\.|$)',
]

print("Testing regex patterns...")
for i, pattern in enumerate(patterns):
    try:
        re.compile(pattern)
        print(f"Pattern {i+1}: OK")
    except re.error as e:
        print(f"Pattern {i+1}: ERROR - {e}")

print("All patterns tested successfully!")
