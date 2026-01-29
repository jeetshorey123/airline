import pdfplumber

# Check Turkish PDF
print("TURKISH PDF CONTENT:")
print("=" * 60)
with pdfplumber.open('turkish.pdf') as pdf:
    text = pdf.pages[0].extract_text()
    # Look for ticket number patterns
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'ticket' in line.lower() or 'eticket' in line.lower() or '2351821130682' in line:
            print(f"Line {i}: {line}")

print("\n" + "=" * 60)
print("\nSRILANKAN PDF CONTENT:")
print("=" * 60)
with pdfplumber.open('srilankan.pdf') as pdf:
    text = pdf.pages[0].extract_text()
    # Look for total and ticket number
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'total' in line.lower() or '48825' in line or '2863063312' in line:
            print(f"Line {i}: {line}")
