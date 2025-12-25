import pdfplumber
import re

pdf = pdfplumber.open('test.pdf')
table = pdf.pages[0].extract_tables()[1]
header = table[0]

print("Header row:")
for i, cell in enumerate(header):
    if cell:
        print(f"  Column {i}: {repr(cell)}")

col_map = {}
for j, cell in enumerate(header):
    if cell:
        cell_lower = str(cell).lower()
        print(f"\nColumn {j}: {repr(cell)}, Lower: {repr(cell_lower)}")
        if 'total' in cell_lower and 'incl' in cell_lower:
            col_map['total_incl'] = j
            print(f"  -> Mapped to total_incl")

print("\nColumn map:", col_map)

if 'total_incl' in col_map:
    grand_total_row = table[3]
    value = grand_total_row[col_map['total_incl']]
    print(f"\nGrand Total Total(Incl Taxes) value: {value}")
