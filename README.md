# Airline Invoice PDF to Excel Converter

A web application that extracts airline invoice data from PDF files and generates downloadable Excel files with structured information.

## Features

- 📄 Upload PDF airline invoices
- 🔍 Automatic data extraction using AI pattern matching
- 📊 Generate Excel files with all invoice details
- 💾 Download extracted data instantly
- 🎨 Modern, user-friendly interface

## Extracted Fields

The application extracts the following information:
- GSTIN
- Invoice/Ticket Number
- Date
- PNR
- Flight Number
- From (Origin)
- To (Destination)
- Place of Supply
- GSTIN of Customer
- Customer Name
- SAC Code
- Taxable Value
- Non-Taxable/Exempted Value
- Total
- Total (Including Taxes)
- Currency

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Upload a PDF invoice file and click "Upload & Convert"

4. The Excel file will be automatically downloaded

## Project Structure

```
airline/
├── app.py                  # Flask backend server
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Frontend interface
├── uploads/               # Temporary PDF storage
├── outputs/               # Generated Excel files
└── README.md             # This file
```

## How It Works

1. User uploads a PDF file through the web interface
2. Backend extracts text from PDF using pdfplumber
3. Regex patterns identify and extract specific invoice fields
4. Data is structured into a pandas DataFrame
5. Excel file is generated with openpyxl
6. File is sent to user for download

## Supported PDF Formats

The application works best with:
- Airline invoice PDFs
- GST invoice PDFs
- Flight ticket PDFs

## Notes

- Maximum file size: 16MB
- Supported format: PDF only
- The extraction accuracy depends on PDF structure
- For best results, use PDFs with clear text formatting

## Technologies Used

- **Backend**: Flask (Python)
- **PDF Processing**: pdfplumber
- **Excel Generation**: pandas, openpyxl
- **Frontend**: HTML, CSS, JavaScript
- **File Handling**: Werkzeug

## License

Free to use and modify
