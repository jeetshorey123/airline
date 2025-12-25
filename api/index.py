from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import io

app = Flask(__name__, template_folder='../templates')
CORS(app)

# Configuration for Vercel (use /tmp directory)
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Create necessary folders
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_data_from_pdf(pdf_path):
    """Extract invoice data from PDF using advanced extraction methods"""
    data = {
        'GSTIN': '',
        'GSTIN of Customer': '',
        'Number': '',
        'GSTIN Customer Name': '',
        'Date': '',
        'PNR': '',
        'From': '',
        'To': '',
        'Taxable Value': '',
        'CGST': '',
        'SGST': '',
        'IGST': '',
        'CESS': '',
        'Total': '',
        'Total(Incl Taxes)': '',
        'Currency': ''
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ''
            all_tables = []
            
            for page in pdf.pages:
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + '\n'
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
            
            # Extract GSTIN patterns (15 character alphanumeric)
            gstin_pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'
            gstins = re.findall(gstin_pattern, full_text)
            if len(gstins) > 0:
                data['GSTIN'] = gstins[0]
            if len(gstins) > 1:
                data['GSTIN of Customer'] = gstins[1]
            
            # Extract Number (pattern: "Number : NL1252608AA53759")
            number_pattern = r'Number[:\s]+([A-Z0-9]+)'
            number_match = re.search(number_pattern, full_text, re.IGNORECASE)
            if number_match:
                data['Number'] = number_match.group(1)
            
            # Extract GSTIN Customer Name (company name after GSTIN Customer Name label)
            gstin_customer_name_patterns = [
                r'GSTIN\s+Customer\s+Name[:\s]*([A-Z][A-Z0-9\s&.,\-]+(?:PVT|LTD|LIMITED|PRIVATE|INC|CORP|LLC)[A-Z\s.]*)',
                r'Customer\s+Name[:\s]*([A-Z][A-Z0-9\s&.,\-]+(?:PVT|LTD|LIMITED|PRIVATE|INC|CORP|LLC)[A-Z\s.]*)',
                r'Bill\s+To[:\s]*\n?([A-Z][A-Z0-9\s&.,\-]+(?:PVT|LTD|LIMITED|PRIVATE|INC|CORP|LLC)[A-Z\s.]*)',
                r'Sold\s+To[:\s]*\n?([A-Z][A-Z0-9\s&.,\-]+(?:PVT|LTD|LIMITED|PRIVATE|INC|CORP|LLC)[A-Z\s.]*)'
            ]
            for pattern in gstin_customer_name_patterns:
                name_match = re.search(pattern, full_text, re.IGNORECASE)
                if name_match:
                    customer_name = name_match.group(1).strip()
                    # Clean up the name (remove extra spaces, newlines)
                    customer_name = re.sub(r'\s+', ' ', customer_name)
                    data['GSTIN Customer Name'] = customer_name
                    break
            
            # Extract PNR (6 character alphanumeric)
            pnr_pattern = r'PNR[:\s]*([A-Z0-9]{6})'
            pnr_match = re.search(pnr_pattern, full_text, re.IGNORECASE)
            if pnr_match:
                data['PNR'] = pnr_match.group(1)
            
            # Extract Date patterns
            date_patterns = [
                r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b',
                r'\b(\d{2}[-/]\w{3}[-/]\d{4})\b',
                r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b'
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, full_text)
                if date_match:
                    data['Date'] = date_match.group(1)
                    break
            
            # Extract From/To (airport codes) - Enhanced patterns
            # Pattern 1: Three letter codes with separator
            route_pattern1 = r'\b([A-Z]{3})\s*[-–>→]\s*([A-Z]{3})\b'
            route_match = re.search(route_pattern1, full_text)
            if route_match:
                data['From'] = route_match.group(1)
                data['To'] = route_match.group(2)
            else:
                # Pattern 2: Look for "From: XXX To: YYY" or similar
                from_pattern = r'(?:From|Origin|Departure|Dept?|DEP)[:\s]*([A-Z]{3})'
                to_pattern = r'(?:To|Destination|Arrival|Arr|ARR)[:\s]*([A-Z]{3})'
                from_match = re.search(from_pattern, full_text, re.IGNORECASE)
                to_match = re.search(to_pattern, full_text, re.IGNORECASE)
                if from_match:
                    data['From'] = from_match.group(1)
                if to_match:
                    data['To'] = to_match.group(1)
                    
                # Pattern 3: Check tables for route information
                if not data['From'] or not data['To']:
                    for table in all_tables:
                        for row in table:
                            if row:
                                row_text = ' '.join([str(cell) for cell in row if cell])
                                route_match_table = re.search(r'\b([A-Z]{3})\s*[-–>→]\s*([A-Z]{3})\b', row_text)
                                if route_match_table:
                                    data['From'] = route_match_table.group(1)
                                    data['To'] = route_match_table.group(2)
                                    break
            
            # Extract Currency
            currency_pattern = r'\b(INR|USD|EUR|GBP|AED)\b'
            currency_match = re.search(currency_pattern, full_text)
            if currency_match:
                data['Currency'] = currency_match.group(1)
            else:
                data['Currency'] = 'INR'
            
            # Smart table-based extraction for GST invoice tables
            for table in all_tables:
                if len(table) > 2:  # Has header + data rows
                    # Find header row with tax columns
                    header_row = None
                    for i, row in enumerate(table):
                        row_text = ' '.join([str(cell) for cell in row if cell])
                        if 'IGST' in row_text and 'CGST' in row_text:
                            header_row = i
                            break
                    
                    if header_row is not None and header_row + 1 < len(table):
                        # Map column indices
                        col_map = {}
                        for j, cell in enumerate(table[header_row]):
                            if cell:
                                cell_lower = str(cell).lower()
                                if 'sac' in cell_lower and 'code' in cell_lower:
                                    col_map['sac'] = j
                                elif 'taxable' in cell_lower and 'value' in cell_lower:
                                    col_map['taxable'] = j
                                elif 'nontax' in cell_lower or ('exempt' in cell_lower and 'value' in cell_lower):
                                    col_map['nontaxable'] = j
                                elif 'igst' in cell_lower:
                                    col_map['igst'] = j
                                elif 'cgst' in cell_lower:
                                    col_map['cgst'] = j
                                elif 'sgst' in cell_lower or 'ugst' in cell_lower:
                                    col_map['sgst'] = j
                                elif 'cess' in cell_lower:
                                    col_map['cess'] = j
                                elif 'total' in cell_lower and 'incl' in cell_lower:
                                    col_map['total_incl'] = j
                                elif 'total' in cell_lower and 'incl' not in cell_lower:
                                    col_map['total'] = j
                        
                        # Extract values from data rows (usually the row after header or 2 rows after)
                        for data_row_idx in range(header_row + 1, min(header_row + 5, len(table))):
                            data_row = table[data_row_idx]
                            
                            # Skip rows with "Tax %" or "Amount" labels
                            row_text = ' '.join([str(cell) for cell in data_row if cell])
                            if 'Tax %' in row_text or 'Amount' in row_text:
                                continue
                            
                            # Determine if this is Grand Total row (prioritize it for totals)
                            is_grand_total = 'grand' in row_text.lower() and 'total' in row_text.lower()
                            
                            # Extract Taxable Value from the correct column
                            if 'taxable' in col_map and (not data['Taxable Value'] or is_grand_total):
                                try:
                                    val = data_row[col_map['taxable']]
                                    if val is not None:
                                        clean_val = str(val).replace(',', '').strip()
                                        if clean_val and re.match(r'^\d+\.?\d*$', clean_val):
                                            data['Taxable Value'] = clean_val
                                            taxable_value = clean_val
                                except:
                                    pass
                            
                            # Extract Total from the correct column (prefer Grand Total row)
                            if 'total' in col_map and (not data['Total'] or is_grand_total):
                                try:
                                    val = data_row[col_map['total']]
                                    if val is not None:
                                        clean_val = str(val).replace(',', '').strip()
                                        if clean_val and re.match(r'^\d+\.?\d*$', clean_val):
                                            data['Total'] = clean_val
                                except:
                                    pass
                            
                            # Extract Total(Incl Taxes) (prefer Grand Total row)
                            if 'total_incl' in col_map and (not data['Total(Incl Taxes)'] or is_grand_total):
                                try:
                                    val = data_row[col_map['total_incl']]
                                    if val is not None:
                                        clean_val = str(val).replace(',', '').strip()
                                        if clean_val and re.match(r'^\d+\.?\d*$', clean_val):
                                            data['Total(Incl Taxes)'] = clean_val
                                except:
                                    pass
                            
                            # Extract GST amounts using the Amount columns (prefer Grand Total row)
                            # IGST Amount
                            if 'igst' in col_map and (not data['IGST'] or is_grand_total):
                                try:
                                    idx = col_map['igst'] + 1  # Amount column is next to IGST header
                                    if idx < len(data_row) and data_row[idx] is not None:
                                        val = str(data_row[idx]).replace(',', '').strip()
                                        if val and re.match(r'^\d+\.?\d*$', val):
                                            data['IGST'] = val
                                except:
                                    pass
                            
                            # CGST Amount
                            if 'cgst' in col_map and (not data['CGST'] or is_grand_total):
                                try:
                                    idx = col_map['cgst'] + 1
                                    if idx < len(data_row) and data_row[idx] is not None:
                                        val = str(data_row[idx]).replace(',', '').strip()
                                        if val and re.match(r'^\d+\.?\d*$', val):
                                            data['CGST'] = val
                                except:
                                    pass
                            
                            # SGST Amount
                            if 'sgst' in col_map and (not data['SGST'] or is_grand_total):
                                try:
                                    idx = col_map['sgst'] + 1
                                    if idx < len(data_row) and data_row[idx] is not None:
                                        val = str(data_row[idx]).replace(',', '').strip()
                                        if val and re.match(r'^\d+\.?\d*$', val):
                                            data['SGST'] = val
                                except:
                                    pass
                            
                            # CESS Amount
                            if 'cess' in col_map and (not data['CESS'] or is_grand_total):
                                try:
                                    idx = col_map['cess'] + 1
                                    if idx < len(data_row) and data_row[idx] is not None:
                                        val = str(data_row[idx]).replace(',', '').strip()
                                        if val and re.match(r'^\d+\.?\d*$', val):
                                            data['CESS'] = val
                                except:
                                    pass
                            
                            # Extract Total(Incl Taxes)
                            if 'total_incl' in col_map and not data['Total(Incl Taxes)']:
                                try:
                                    val = data_row[col_map['total_incl']]
                                    if val:
                                        clean_val = str(val).replace(',', '').strip()
                                        if clean_val and re.match(r'^\d+\.?\d*$', clean_val):
                                            if float(clean_val) > 0:
                                                data['Total(Incl Taxes)'] = clean_val
                                except:
                                    pass
            
            # If still no taxable value from tables, try regex patterns
            if not data['Taxable Value']:
                taxable_value = None
                
                # Try different patterns
                taxable_patterns = [
                    r'Taxable[:\s]*(?:Value|Amount)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Base\s*Fare[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Fare[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Taxable\s*Amt[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
                ]
                
                for pattern in taxable_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        taxable_value = match.group(1).replace(',', '')
                        data['Taxable Value'] = taxable_value
                        break
                
                # Search in tables if not found
                if not taxable_value:
                    for table in all_tables:
                        for i, row in enumerate(table):
                            if row:
                                for j, cell in enumerate(row):
                                    if cell and re.search(r'taxable|base.*fare|fare', str(cell), re.IGNORECASE):
                                        # Look for number in same row or next cells
                                        for k in range(j, len(row)):
                                            if row[k]:
                                                amount_match = re.search(r'([0-9,]+\.?\d+)', str(row[k]))
                                                if amount_match:
                                                    taxable_value = amount_match.group(1).replace(',', '')
                                                    if float(taxable_value) > 0:
                                                        data['Taxable Value'] = taxable_value
                                                        break
                                        if data['Taxable Value']:
                                            break
                            if data['Taxable Value']:
                                break
                        if data['Taxable Value']:
                            break
            else:
                taxable_value = data['Taxable Value']
            
            # Extract CGST - Enhanced extraction with table support
            cgst_value = None
            cgst_patterns = [
                r'CGST[:\s@]*(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Central\s*GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'C\.?GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
            ]
            for pattern in cgst_patterns:
                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                for cgst_match in matches:
                    candidate = cgst_match.group(1).replace(',', '')
                    # Filter: CGST should be less than taxable value
                    try:
                        if taxable_value and 0 < float(candidate) < float(taxable_value):
                            cgst_value = candidate
                            data['CGST'] = cgst_value
                            break
                        elif not taxable_value and 0 < float(candidate) < 100000:
                            cgst_value = candidate
                            data['CGST'] = cgst_value
                            break
                    except:
                        pass
                if cgst_value:
                    break
            
            # Search in tables if not found
            if not cgst_value:
                for table in all_tables:
                    for row in table:
                        if row:
                            for j, cell in enumerate(row):
                                if cell and re.search(r'\bCGST\b|Central.*GST', str(cell), re.IGNORECASE):
                                    for k in range(j + 1, len(row)):
                                        if row[k] and str(row[k]).strip():
                                            amount_match = re.search(r'([0-9,]+\.?\d+)', str(row[k]))
                                            if amount_match:
                                                candidate = amount_match.group(1).replace(',', '')
                                                try:
                                                    if taxable_value and 0 < float(candidate) < float(taxable_value):
                                                        cgst_value = candidate
                                                        data['CGST'] = cgst_value
                                                        break
                                                    elif not taxable_value and 0 < float(candidate):
                                                        cgst_value = candidate
                                                        data['CGST'] = cgst_value
                                                        break
                                                except:
                                                    pass
                                    if data['CGST']:
                                        break
                        if data['CGST']:
                            break
                    if data['CGST']:
                        break
            
            # Extract SGST - Enhanced extraction with table support
            sgst_value = None
            sgst_patterns = [
                r'SGST[:\s@]*(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'State\s*GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'S\.?GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
            ]
            for pattern in sgst_patterns:
                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                for sgst_match in matches:
                    candidate = sgst_match.group(1).replace(',', '')
                    try:
                        if taxable_value and 0 < float(candidate) < float(taxable_value):
                            sgst_value = candidate
                            data['SGST'] = sgst_value
                            break
                        elif not taxable_value and 0 < float(candidate) < 100000:
                            sgst_value = candidate
                            data['SGST'] = sgst_value
                            break
                    except:
                        pass
                if sgst_value:
                    break
            
            # Search in tables if not found
            if not sgst_value:
                for table in all_tables:
                    for row in table:
                        if row:
                            for j, cell in enumerate(row):
                                if cell and re.search(r'\bSGST\b|State.*GST', str(cell), re.IGNORECASE):
                                    for k in range(j + 1, len(row)):
                                        if row[k] and str(row[k]).strip():
                                            amount_match = re.search(r'([0-9,]+\.?\d+)', str(row[k]))
                                            if amount_match:
                                                candidate = amount_match.group(1).replace(',', '')
                                                try:
                                                    if taxable_value and 0 < float(candidate) < float(taxable_value):
                                                        sgst_value = candidate
                                                        data['SGST'] = sgst_value
                                                        break
                                                    elif not taxable_value and 0 < float(candidate):
                                                        sgst_value = candidate
                                                        data['SGST'] = sgst_value
                                                        break
                                                except:
                                                    pass
                                    if data['SGST']:
                                        break
                        if data['SGST']:
                            break
                    if data['SGST']:
                        break
            
            # Extract IGST - Enhanced extraction with table support
            igst_value = None
            igst_patterns = [
                r'IGST[:\s@]*(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Integrated\s*GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'I\.?GST[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
            ]
            for pattern in igst_patterns:
                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                for igst_match in matches:
                    candidate = igst_match.group(1).replace(',', '')
                    try:
                        if taxable_value and 0 < float(candidate) < float(taxable_value):
                            igst_value = candidate
                            data['IGST'] = igst_value
                            break
                        elif not taxable_value and 0 < float(candidate) < 100000:
                            igst_value = candidate
                            data['IGST'] = igst_value
                            break
                    except:
                        pass
                if igst_value:
                    break
            
            # Search in tables if not found
            if not igst_value:
                for table in all_tables:
                    for row in table:
                        if row:
                            for j, cell in enumerate(row):
                                if cell and re.search(r'\bIGST\b|Integrated.*GST', str(cell), re.IGNORECASE):
                                    for k in range(j + 1, len(row)):
                                        if row[k] and str(row[k]).strip():
                                            amount_match = re.search(r'([0-9,]+\.?\d+)', str(row[k]))
                                            if amount_match:
                                                candidate = amount_match.group(1).replace(',', '')
                                                try:
                                                    if taxable_value and 0 < float(candidate) < float(taxable_value):
                                                        igst_value = candidate
                                                        data['IGST'] = igst_value
                                                        break
                                                    elif not taxable_value and 0 < float(candidate):
                                                        igst_value = candidate
                                                        data['IGST'] = igst_value
                                                        break
                                                except:
                                                    pass
                                    if data['IGST']:
                                        break
                        if data['IGST']:
                            break
                    if data['IGST']:
                        break
            
            # Extract CESS
            cess_patterns = [
                r'CESS[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Cess[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
            ]
            for pattern in cess_patterns:
                cess_match = re.search(pattern, full_text)
                if cess_match:
                    data['CESS'] = cess_match.group(1).replace(',', '')
                    break
            
            # Extract Total if not found
            if not data['Total']:
                total_patterns = [
                    r'Sub[\s-]*Total[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Total[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
                ]
                for pattern in total_patterns:
                    total_match = re.search(pattern, full_text, re.IGNORECASE)
                    if total_match:
                        data['Total'] = total_match.group(1).replace(',', '')
                        break
            
            # Extract Total(Incl Taxes)
            if not data['Total(Incl Taxes)']:
                total_incl_patterns = [
                    r'Grand[\s-]*Total[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Total.*(?:Tax|Invoice)[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Invoice[\s-]*Total[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                    r'Net[\s-]*Amount[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)'
                ]
                for pattern in total_incl_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        data['Total(Incl Taxes)'] = match.group(1).replace(',', '')
                        break
    
    except Exception as e:
        print(f"Error extracting data: {str(e)}")
    
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    # Support both 'files[]' and 'files' key names
    files = request.files.getlist('files[]') or request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({'error': 'No files selected'}), 400
    
    if len(files) > 1000:
        return jsonify({'error': 'Maximum 1000 PDF files allowed'}), 400
    
    all_data = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
            file.save(pdf_path)
            
            # Extract data from PDF
            extracted_data = extract_data_from_pdf(pdf_path)
            all_data.append(extracted_data)
            
            # Clean up uploaded PDF
            try:
                os.remove(pdf_path)
            except:
                pass
    
    if len(all_data) == 0:
        return jsonify({'error': 'No valid PDF files found'}), 400
    
    # Create Excel file with all data
    df = pd.DataFrame(all_data)
    excel_filename = f"invoice_data_{timestamp}.xlsx"
    excel_path = os.path.join(app.config['OUTPUT_FOLDER'], excel_filename)
    
    # Save to Excel with formatting
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoice Data')
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Invoice Data']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            # Handle columns beyond Z
            if idx < 26:
                col_letter = chr(65 + idx)
            else:
                col_letter = chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = max_length
    
    return jsonify({
        'success': True,
        'filename': excel_filename,
        'count': len(all_data),
        'data': all_data
    })

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

# This is required for Vercel
app = app
