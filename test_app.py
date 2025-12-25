from app import extract_data_from_pdf
import json

# Add temporary debugging
data = extract_data_from_pdf('test.pdf')
print(json.dumps(data, indent=2))
