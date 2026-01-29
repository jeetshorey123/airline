import pdfplumber

with pdfplumber.open('srilankan.pdf') as pdf:
    text = pdf.pages[0].extract_text()
    
    print("Full Sri Lankan PDF Content:")
    print("=" * 80)
    print(text)
    print("\n" + "=" * 80)
    
    # Check for tax values
    print("\nLines with numbers:")
    for i, line in enumerate(text.split('\n')):
        if any(tax in line.lower() for tax in ['igst', 'cgst', 'sgst', 'tax', 'total', '48825', '2325']):
            print(f"Line {i}: {line}")
