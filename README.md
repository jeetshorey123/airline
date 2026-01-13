# Airline Invoice PDF to Excel Converter

Extract airline invoice data from PDF files and generate Excel spreadsheets.

## Features

- Upload multiple airline PDF invoices
- Automatic extraction of invoice details
- Excel file generation with all extracted data
- Support for 10+ airlines (Indigo, Air India, Kuwait, Malaysia, etc.)

## Extracted Fields

- GSTIN, Invoice Number, Date, PNR
- Flight Number, From, To, Place of Supply
- Customer Details (GSTIN, Name)
- SAC Code
- Taxable Value, CGST, SGST, IGST, Cess
- Total (Including Taxes)

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Deployment

Deployed on Vercel at `/api/index.py`

## Technologies

- Flask 3.0.0, pdfplumber 0.10.3
- pandas 2.1.4, openpyxl 3.1.2
- Pattern-based extraction with regex
