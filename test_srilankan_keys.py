from app import extract_data_srilankan

data = extract_data_srilankan('srilankan.pdf')
print("All extracted fields:")
for key, value in data.items():
    print(f"{key}: {value}")
