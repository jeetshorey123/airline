from app import extract_data_turkish, extract_data_srilankan

# Test Turkish extraction
print("TURKISH Extraction:")
print("=" * 60)
turkish_data = extract_data_turkish('turkish.pdf')
print(f"Ticket Number: {turkish_data.get('Ticket Number', 'Not found')}")
print(f"Total (inc taxes): {turkish_data.get('Total(Incl Taxes)', 'Not found')}")
print(f"CGST: {turkish_data.get('CGST', 'Not found')}")
print(f"SGST: {turkish_data.get('SGST', 'Not found')}")
print(f"IGST: {turkish_data.get('IGST', 'Not found')}")
print(f"Tax Summary: {turkish_data.get('Tax Summary', 'Not found')}")
print()

# Test Sri Lankan extraction
print("SRILANKAN Extraction:")
print("=" * 60)
srilankan_data = extract_data_srilankan('srilankan.pdf')
print(f"Ticket Number: {srilankan_data.get('Ticket Number', 'Not found')}")
print(f"Total (inc taxes): {srilankan_data.get('Total(Incl Taxes)', 'Not found')}")
print(f"Taxable Value: {srilankan_data.get('Taxable Value', 'Not found')}")
print(f"CGST: {srilankan_data.get('CGST', 'Not found')}")
print(f"SGST: {srilankan_data.get('SGST', 'Not found')}")
print(f"IGST: {srilankan_data.get('IGST', 'Not found')}")
print(f"Tax Summary: {srilankan_data.get('Tax Summary', 'Not found')}")

