import pdfplumber
import re

with pdfplumber.open('turkish.pdf') as pdf:
    text = pdf.pages[0].extract_text()
    
    # Test different patterns
    patterns = [
        (r'\b([0-9]{13})\s+\d{2}/\d{2}/\d{2}', 'Pattern 1: number followed by date'),
        (r'1\s+([0-9]{13})\s+', 'Pattern 2: 1 space number'),
        (r'Srl.*?(\d{13})', 'Pattern 3: After Srl'),
    ]
    
    print("Testing patterns on Turkish PDF:")
    print("=" * 60)
    for pattern, desc in patterns:
        match = re.search(pattern, text)
        if match:
            print(f"✓ {desc}: {match.group(1)}")
        else:
            print(f"✗ {desc}: No match")
    
    print("\nRelevant lines:")
    print("=" * 60)
    for line in text.split('\n')[15:25]:
        print(line)
