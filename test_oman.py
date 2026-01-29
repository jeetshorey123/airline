from app import extract_data_oman

o2 = extract_data_oman('oman (2).pdf')
print('OMAN(2) Extraction:')
print('=' * 60)
print(f'Ticket Number: {o2["Ticket Number"]}')
print(f'CGST: {o2["CGST"]}')
print(f'SGST: {o2["SGST"]}')
print(f'IGST: {o2["IGST"]}')
print(f'Tax Summary: {o2["Tax Summary"]}')
