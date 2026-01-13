from flask import Flask, render_template, request, send_file, jsonify, Response
from flask_cors import CORS
import pdfplumber
import pandas as pd
import re
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import time

app = Flask(__name__, template_folder='../templates')
CORS(app)

# Global progress tracking
progress_data = {'current': 0, 'total': 0, 'status': 'idle', 'message': ''}

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

# ================================================================================
# UNIFIED PDF PREPROCESSING
# ================================================================================

class PDFPreprocessor:
    """Unified PDF preprocessing to standardize data extraction"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.full_text = ''
        self.all_tables = []
        self.lines = []
        self.numeric_values = []
        
    def extract_content(self):
        """Extract all content from PDF in a standardized way"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        self.full_text += page_text + '\n'
                    
                    # Extract tables with better settings
                    tables = page.extract_tables({
                        'vertical_strategy': 'lines',
                        'horizontal_strategy': 'lines',
                        'snap_tolerance': 3,
                        'join_tolerance': 3,
                        'edge_min_length': 3,
                    })
                    if tables:
                        self.all_tables.extend(tables)
                
                # Split into lines for line-by-line analysis
                self.lines = self.full_text.split('\n')
                
                # Extract all numeric values with context
                self._extract_numeric_values()
                
        except Exception as e:
            print(f"Error in PDF preprocessing: {str(e)}")
    
    def _extract_numeric_values(self):
        """Extract all numeric values from text with their context"""
        for i, line in enumerate(self.lines):
            # Find all numbers in the line
            numbers = re.findall(r'([0-9,]+\.?\d*)', line)
            for num_str in numbers:
                try:
                    clean_num = num_str.replace(',', '')
                    if re.match(r'^\d+\.?\d*$', clean_num):
                        self.numeric_values.append({
                            'value': float(clean_num),
                            'string': clean_num,
                            'line_index': i,
                            'context': line.strip(),
                            'prev_line': self.lines[i-1].strip() if i > 0 else '',
                            'next_line': self.lines[i+1].strip() if i < len(self.lines)-1 else ''
                        })
                except:
                    pass
        
        # Sort by value for easier range-based extraction
        self.numeric_values.sort(key=lambda x: x['value'])
    
    def get_content(self):
        """Return all extracted content"""
        return {
            'full_text': self.full_text,
            'tables': self.all_tables,
            'lines': self.lines,
            'numeric_values': self.numeric_values
        }

# ================================================================================
# UNIFIED DATA EXTRACTOR
# ================================================================================

class UnifiedDataExtractor:
    """Unified extraction logic for all airlines"""
    
    def __init__(self, content, airline_name='UNKNOWN'):
        self.content = content
        self.full_text = content['full_text']
        self.tables = content['tables']
        self.lines = content['lines']
        self.numeric_values = content['numeric_values']
        self.airline_name = airline_name
        
        # Initialize data structure
        self.data = {
            'Airline': airline_name,
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
            'Total(Incl Taxes)': ''
        }
    
    def extract_gstins(self):
        """Extract GSTIN numbers (15 character alphanumeric)"""
        gstin_pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'
        gstins = re.findall(gstin_pattern, self.full_text)
        if len(gstins) > 0:
            self.data['GSTIN'] = gstins[0]
        if len(gstins) > 1:
            self.data['GSTIN of Customer'] = gstins[1]
    
    def extract_invoice_number(self, patterns=None):
        """Extract invoice number with multiple patterns"""
        if patterns is None:
            patterns = [
                r'Ticket\s*No[:\-]+\s*([0-9]+)',  # Kuwait: Ticket No:- 2296321387874
                r'Serial\s*No\.?[:\s]+([0-9]+)',  # SriLankan: Serial No.: 2863063312
                r'(?:Invoice|Tax Invoice|Bill|Receipt)\s*(?:No|Number|#)[:\s]*([A-Z0-9\-/]+)',
                r'Number[:\s]+([A-Z0-9]+)',
                r'Invoice\s*No\s*[:\s]*([A-Z0-9]+[/-]\d+[/-]\d+)',
                r'Invoice\s*Number[:\s]*([A-Z0-9]+)',
            ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                self.data['Number'] = match.group(1).strip()
                break
    
    def extract_customer_name(self, patterns=None):
        """Extract customer name with multiple patterns"""
        if patterns is None:
            patterns = [
                # Qatar - Name TATA... (no colon, name on same line)
                r'Details\s+of\s+Recipient[\s\S]{0,100}?Name\s+([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT|COMPANY))',
                # Air India - Customer :
                r'Customer\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # Akasa - Name of Customer:
                r'Name\s+of\s+Customer\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # Oman - Billed to: (skip first line with Oman Air)
                r'Billed\s+to\s*:\s*(?:[^\n]*\n)?([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # Qatar - Simple Name: or Name (without colon)
                r'Name\s*:?\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # Kuwait - TATA CONSULTANCY on left side after airline name
                r'KUWAIT AIRWAYS COMPANY\s+([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # SriLankan - Bill to Address
                r'Bill\s+to\s+Address\s+([A-Z]+)',
                # Turkish - Recipient details:
                r'Recipient\s+details\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                # Generic patterns
                r'GSTIN\s+Customer\s+Name\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                r'Customer\s+Name\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
                r'Bill\s+[Tt]o\s*:\s*([A-Z][A-Z\s&]+(?:LIMITED|LTD|SERVICES|PRIVATE|PVT))',
            ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE | re.MULTILINE)
            if match:
                customer_name = match.group(1).strip()
                # Clean up the name - normalize spaces and remove unwanted prefixes
                customer_name = re.sub(r'\s+', ' ', customer_name)
                # Remove airline names that might be captured
                customer_name = re.sub(r'^(Oman Air SAOC|Qatar Airways|Turkish Airlines|Kuwait Airways)\s+', '', customer_name, flags=re.IGNORECASE)
                self.data['GSTIN Customer Name'] = customer_name
                break
    
    def extract_date(self, patterns=None):
        """Extract date with multiple format support"""
        if patterns is None:
            patterns = [
                (r'(?:Invoice\s*)?Date[:\s]*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', '%d %b %Y'),  # DD Mon YYYY (Indigo)
                (r'(?:Invoice\s*)?Date[:\s]*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4})', '%d-%b-%Y'),  # DD-MMM-YYYY
                (r'(?:Invoice\s*)?Date[:\s]*(\d{1,2}[-/]\d{2}[-/]\d{4})', '%d-%m-%Y'),  # DD-MM-YYYY
                (r'Invoice\s*Dt[:\s]*(\d{1,2}[-/]\d{2}[-/]\d{4})', '%d-%m-%Y'),  # Invoice Dt (Turkish)
                (r'(?:Invoice\s*)?Date[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})', '%Y-%m-%d'),  # YYYY-MM-DD
                (r'(?:Invoice\s*)?Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})', '%d/%m/%Y'),  # DD/MM/YYYY
                (r'\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})\b', '%d-%b-%Y'),  # DD-MMM-YYYY standalone (Kuwait)
                (r'\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2})\b', '%d-%b-%y'),  # DD-MMM-YY
                (r'\b(\d{1,2}th\s+[A-Za-z]+\s+\d{4})\b', '%dth %B %Y'),  # DDth Month YYYY
            ]
        
        for pattern, date_format in patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                self.data['Date'] = match.group(1).strip()
                break
    
    def extract_pnr(self, patterns=None):
        """Extract PNR with multiple patterns"""
        if patterns is None:
            patterns = [
                r'PNR[:\s]*([A-Z0-9]{6})',
                r'PNR\s+No\s*[:\s]*([A-Z0-9]{6})',
                r'Booking\s*(?:Ref|Reference)[:\s]*([A-Z0-9]{6})',
                r'Confirmation\s*(?:No|Number)[:\s]*([A-Z0-9]{6})',
                r'Ticket\s+Reference[:\s]*\n\s*[A-Z]\s+([A-Z0-9]{6})',  # SriLankan format
            ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE | re.MULTILINE)
            if match:
                self.data['PNR'] = match.group(1).strip()
                break
    
    def extract_route(self):
        """Extract From/To airport codes"""
        # Pattern 1: XXX-XXX or XXX>XXX format
        route_patterns = [
            r'\b([A-Z]{3})\s*[-–>→]\s*([A-Z]{3})\b',
            r'(?:From|Origin|Departure)[:\s]*([A-Z]{3})',
            r'(?:To|Destination|Arrival)[:\s]*([A-Z]{3})',
        ]
        
        route_match = re.search(route_patterns[0], self.full_text)
        if route_match:
            self.data['From'] = route_match.group(1)
            self.data['To'] = route_match.group(2)
        else:
            # Try separate From/To extraction
            from_match = re.search(route_patterns[1], self.full_text, re.IGNORECASE)
            to_match = re.search(route_patterns[2], self.full_text, re.IGNORECASE)
            if from_match:
                self.data['From'] = from_match.group(1)
            if to_match:
                self.data['To'] = to_match.group(1)
    
    def extract_financial_data_from_tables(self):
        """Enhanced table-based financial data extraction"""
        for table in self.tables:
            if len(table) < 2:
                continue
            
            # Find header row
            header_row_idx = None
            col_map = {}
            
            for i, row in enumerate(table):
                row_text = ' '.join([str(cell).upper() if cell else '' for cell in row])
                
                # Identify header by looking for key column names
                if any(keyword in row_text for keyword in ['TAXABLE', 'IGST', 'CGST', 'SGST', 'TOTAL']):
                    header_row_idx = i
                    
                    # Map columns
                    for j, cell in enumerate(row):
                        if cell:
                            cell_lower = str(cell).lower()
                            cell_str = str(cell)
                            # Taxable Value - exclude 'Non Taxable' columns
                            if 'taxable' in cell_lower and 'value' in cell_lower and 'non' not in cell_lower:
                                col_map['taxable'] = j
                            elif 'igst' in cell_lower:
                                # Check if header already contains amount (with %) or just label
                                col_map['igst'] = j
                                col_map['igst_has_percent'] = '%' in cell_str
                            elif 'cgst' in cell_lower:
                                col_map['cgst'] = j
                                col_map['cgst_has_percent'] = '%' in cell_str
                            elif 'sgst' in cell_lower or 'ugst' in cell_lower:
                                col_map['sgst'] = j
                                col_map['sgst_has_percent'] = '%' in cell_str
                            elif 'cess' in cell_lower:
                                col_map['cess'] = j
                            elif 'total' in cell_lower and ('incl' in cell_lower or 'invoice' in cell_lower or 'ticket' in cell_lower):
                                col_map['total_incl'] = j
                    break
            
            if header_row_idx is None:
                continue
            
            # Extract data from rows after header
            for data_row_idx in range(header_row_idx + 1, min(header_row_idx + 10, len(table))):
                data_row = table[data_row_idx]
                if not data_row:
                    continue
                
                # Skip rows where all non-None cells are just labels (sub-headers)
                non_none_cells = [cell for cell in data_row if cell]
                if not non_none_cells:
                    continue
                
                # Skip sub-header rows (e.g., "Taxable*", "Non Taxable*")
                row_has_only_labels = all(
                    not any(char.isdigit() for char in str(cell))
                    for cell in non_none_cells
                )
                if row_has_only_labels and not any('total' in str(cell).lower() for cell in non_none_cells):
                    continue
                
                row_text = ' '.join([str(cell) if cell else '' for cell in data_row])
                is_total_row = 'total' in row_text.lower() or 'grand' in row_text.lower()
                
                # Extract values from mapped columns
                if 'taxable' in col_map and not self.data['Taxable Value']:
                    val = self._get_cell_value(data_row, col_map['taxable'])
                    if val:
                        self.data['Taxable Value'] = val
                
                if 'igst' in col_map:
                    # If header has % (e.g., "IGST\n12%"), amount is in same column
                    # Otherwise, amount is usually next column after IGST label
                    if col_map.get('igst_has_percent', False):
                        val = self._get_cell_value(data_row, col_map['igst'])
                    else:
                        val = self._get_cell_value(data_row, col_map['igst'] + 1 if col_map['igst'] + 1 < len(data_row) else col_map['igst'])
                    if val and (not self.data['IGST'] or is_total_row):
                        self.data['IGST'] = val
                
                if 'cgst' in col_map:
                    if col_map.get('cgst_has_percent', False):
                        val = self._get_cell_value(data_row, col_map['cgst'])
                    else:
                        val = self._get_cell_value(data_row, col_map['cgst'] + 1 if col_map['cgst'] + 1 < len(data_row) else col_map['cgst'])
                    if val and (not self.data['CGST'] or is_total_row):
                        self.data['CGST'] = val
                
                if 'sgst' in col_map:
                    if col_map.get('sgst_has_percent', False):
                        val = self._get_cell_value(data_row, col_map['sgst'])
                    else:
                        val = self._get_cell_value(data_row, col_map['sgst'] + 1 if col_map['sgst'] + 1 < len(data_row) else col_map['sgst'])
                    if val and (not self.data['SGST'] or is_total_row):
                        self.data['SGST'] = val
                
                if 'cess' in col_map:
                    val = self._get_cell_value(data_row, col_map['cess'] + 1 if col_map['cess'] + 1 < len(data_row) else col_map['cess'])
                    if val and (not self.data['CESS'] or is_total_row):
                        self.data['CESS'] = val
                
                if 'total_incl' in col_map:
                    val = self._get_cell_value(data_row, col_map['total_incl'])
                    if val and (not self.data['Total(Incl Taxes)'] or is_total_row):
                        self.data['Total(Incl Taxes)'] = val
    
    def _get_cell_value(self, row, col_idx):
        """Safely extract numeric value from table cell"""
        try:
            if col_idx < len(row) and row[col_idx] is not None:
                val_str = str(row[col_idx]).replace(',', '').strip()
                # Allow 0 values (e.g., CGST=0, SGST=0)
                if re.match(r'^\d+\.?\d*$', val_str):
                    return val_str
        except:
            pass
        return None
    
    def extract_financial_data_from_text(self):
        """Extract financial data from text using patterns"""
        # Taxable Value
        if not self.data['Taxable Value']:
            patterns = [
                r'Taxable\s+Value\s+of\s+Services\s+\(INR\)[\s]*([0-9,]+\.?\d*)',  # Kuwait: Taxable Value of Services (INR) 34,358.00
                r'996425\s+\d+\s+([0-9,]+)\s+\d+\s+IGST',  # Oman: 996425 0 24576 5 IGST: 1229
                r'996425\s+₹\s+[0-9,]+\.?\d*\s+₹\s+[0-9,]+\.?\d*\s+₹\s+([0-9,]+\.?\d*)',  # Qatar: 996425 ₹ 68,026.00 ₹ 5,173.00 ₹ 68,026.00
                r'BZYSW3\s+([0-9,]+)',  # SriLankan: Ticket ref BZYSW3 46500
                r'996425\s+\d+\s+[A-Z]+\s+\d{2}-[A-Z][a-z]{2}-\d{2}\s+[A-Z]+\s+([0-9,]+\.?\d*)',  # Malaysia: 996425 2322791265500 TKTT 25-Sep-25 ECONOMY 8105.00
                r'Taxable\s+Value\s+₹[\s\-]*([0-9,]+\.?\d*)',  # Oman header format
                r'Taxable\s+Value[\s\-]*₹[\s]*([0-9,]+\.?\d*)',  # Qatar header format
                r'Taxable\s+Value[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Base\s+Fare[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'996411[^\d]*([0-9,]+\.?\d*)',  # SAC code for air transport
            ]
            for pattern in patterns:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).replace(',', '')
                    try:
                        if float(val) > 0:
                            self.data['Taxable Value'] = val
                            break
                    except:
                        pass
        
        # IGST
        if not self.data['IGST']:
            patterns = [                r'Intergrated\s+Tax\s+\(IGST\)\s+[\d.]+%?\s+([0-9,]+\.?\d*)',  # Kuwait: Intergrated Tax (IGST) 5 1,718.00                r'IGST[:\s]*(?:@\s*)?(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Integrated\s+Tax[:\s]*([0-9,]+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).replace(',', '')
                    try:
                        if float(val) > 0:
                            self.data['IGST'] = val
                            break
                    except:
                        pass
        
        # CGST
        if not self.data['CGST']:
            patterns = [
                r'CGST[:\s]*(?:@\s*)?(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Central\s+(?:GST|Tax)[:\s]*([0-9,]+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).replace(',', '')
                    try:
                        if float(val) > 0:
                            self.data['CGST'] = val
                            break
                    except:
                        pass
        
        # SGST
        if not self.data['SGST']:
            patterns = [
                r'SGST[:\s]*(?:@\s*)?(?:[\d.]+%)?[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'State\s+(?:GST|Tax)[:\s]*([0-9,]+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).replace(',', '')
                    try:
                        if float(val) > 0:
                            self.data['SGST'] = val
                            break
                    except:
                        pass
        
        # Total (Incl Taxes)
        if not self.data['Total(Incl Taxes)']:
            patterns = [
                r'Total\s+Invoice\s+Value\s+including\s+taxes\s+([0-9,]+\.?\d*)',  # Kuwait: Total Invoice Value including taxes 40,524.00
                r'Total\s+(?:Ticket\s+)?Value[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Total\s+Invoice\s+Value[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'Grand\s+Total[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
                r'(?:Net|Final)\s+Amount[:\s]*(?:Rs\.?|INR|₹)?[\s]*([0-9,]+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, self.full_text, re.IGNORECASE)
                if match:
                    val = match.group(1).replace(',', '')
                    try:
                        if float(val) > 0:
                            self.data['Total(Incl Taxes)'] = val
                            break
                    except:
                        pass
    
    def apply_post_extraction_logic(self):
        """Apply airline-specific post-processing and calculations"""
        # SriLankan Airlines: Fix SGST/IGST mislabeling for international flights
        if self.airline_name == 'SRILANKAN AIRLINES':
            # If SGST has value but IGST is empty, and CGST is empty, move SGST to IGST
            # (International flights should have IGST, not SGST)
            if self.data['SGST'] and not self.data['IGST'] and not self.data['CGST']:
                self.data['IGST'] = self.data['SGST']
                self.data['SGST'] = '0'
                self.data['CGST'] = '0'
        
        # Set CGST/SGST to 0 for international flights (IGST only)
        if self.data['IGST'] and not self.data['CGST']:
            self.data['CGST'] = '0'
        if self.data['IGST'] and not self.data['SGST']:
            self.data['SGST'] = '0'
        
        # Calculate missing Taxable Value
        if not self.data['Taxable Value'] and self.data['Total(Incl Taxes)']:
            try:
                total_incl = float(self.data['Total(Incl Taxes)'])
                cgst = float(self.data['CGST']) if self.data['CGST'] else 0
                sgst = float(self.data['SGST']) if self.data['SGST'] else 0
                igst = float(self.data['IGST']) if self.data['IGST'] else 0
                taxable = total_incl - (cgst + sgst + igst)
                if taxable > 0:
                    self.data['Taxable Value'] = str(round(taxable, 2))
            except:
                pass
        
        # Calculate missing Total(Incl Taxes)
        if not self.data['Total(Incl Taxes)'] and self.data['Taxable Value']:
            try:
                taxable = float(self.data['Taxable Value'])
                cgst = float(self.data['CGST']) if self.data['CGST'] else 0
                sgst = float(self.data['SGST']) if self.data['SGST'] else 0
                igst = float(self.data['IGST']) if self.data['IGST'] else 0
                total_incl = taxable + cgst + sgst + igst
                if total_incl > 0:
                    self.data['Total(Incl Taxes)'] = str(round(total_incl, 2))
            except:
                pass
        
        # Format date for Indigo
        if self.airline_name == 'INDIGO' and self.data['Date']:
            self.data['Date'] = self._format_date_indigo(self.data['Date'])
    
    def _format_date_indigo(self, date_str):
        """Format date to DD Mon YYYY for Indigo"""
        try:
            date_formats = [
                ('%d-%b-%Y', r'\d{2}-[A-Za-z]{3}-\d{4}'),
                ('%d-%b-%y', r'\d{2}-[A-Za-z]{3}-\d{2}'),
                ('%d/%m/%Y', r'\d{2}/\d{2}/\d{4}'),
                ('%d-%m-%Y', r'\d{2}-\d{2}-\d{4}'),
                ('%Y-%m-%d', r'\d{4}-\d{2}-\d{2}'),
            ]
            
            for date_format, pattern in date_formats:
                if re.match(pattern, date_str):
                    try:
                        parsed_date = datetime.strptime(date_str, date_format)
                        return parsed_date.strftime('%d %b %Y')
                    except:
                        continue
        except:
            pass
        return date_str
    
    def extract_all(self):
        """Run all extraction methods"""
        self.extract_gstins()
        self.extract_invoice_number()
        self.extract_customer_name()
        self.extract_date()
        self.extract_pnr()
        self.extract_route()
        self.extract_financial_data_from_tables()
        self.extract_financial_data_from_text()
        self.apply_post_extraction_logic()
        return self.data

# ================================================================================
# AIRLINE-SPECIFIC EXTRACTORS (Using Unified System)
# ================================================================================

def detect_airline(pdf_path):
    """Detect airline from PDF content"""
    try:
        preprocessor = PDFPreprocessor(pdf_path)
        preprocessor.extract_content()
        content = preprocessor.get_content()
        text_upper = content['full_text'].upper()
        
        # Check for airline-specific patterns
        if 'MALAYSIAN AIRLINES' in text_upper or 'MALAYSIA AIRLINES' in text_upper:
            return 'malaysia'
        elif 'TURKISH AIRLINES' in text_upper:
            return 'turkish'
        elif 'SRILANKAN AIRLINES' in text_upper or 'SRILANKA' in text_upper:
            return 'srilankan'
        elif 'QATAR AIRWAYS' in text_upper:
            return 'qatar'
        elif 'OMAN AIR' in text_upper:
            return 'oman'
        elif 'KUWAIT AIRWAYS' in text_upper:
            return 'kuwait'
        elif 'AIR INDIA EXPRESS' in text_upper:
            return 'airindiaexpress'
        elif 'AIR INDIA' in text_upper and 'DEBIT NOTE' in text_upper:
            return 'airindia'
        elif 'AKASA' in text_upper or 'AKASA AIR' in text_upper:
            return 'akasa'
        elif 'INDIGO' in text_upper or '6E' in text_upper:
            return 'indigo'
        else:
            return 'indigo'  # Default to Indigo
    except:
        return 'indigo'

def extract_data_from_pdf(pdf_path):
    """Extract data from Indigo PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'INDIGO')
    return extractor.extract_all()

def extract_data_airindia(pdf_path):
    """Extract data from Air India PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'AIR INDIA')
    extractor.extract_invoice_number([
        r'Debit\s*Note\s*(?:No|Number)[:\s]*([A-Z0-9]+)',
        r'Invoice\s*(?:No|Number)[:\s]*([A-Z0-9]+)',
    ])
    extractor.extract_all()
    return extractor.data

def extract_data_airindiaexpress(pdf_path):
    """Extract data from Air India Express PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'AIR INDIA EXPRESS')
    extractor.extract_all()
    return extractor.data

def extract_data_kuwait(pdf_path):
    """Extract data from Kuwait Airways PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'KUWAIT AIRWAYS')
    extractor.extract_gstins()
    extractor.extract_invoice_number([
        r'Ticket\s*No[:\-]+\s*([0-9]+)',
        r'([A-Z]{3}/[A-Z][a-z]{2}/\d{2}/\d+)',
        r'Invoice\s*(?:No|Number)[:\s]*([A-Z0-9\-/]+)',
    ])
    extractor.extract_customer_name()
    extractor.extract_date()
    extractor.extract_pnr()
    extractor.extract_route()
    extractor.extract_financial_data_from_tables()
    extractor.extract_financial_data_from_text()
    extractor.apply_post_extraction_logic()
    return extractor.data

def extract_data_oman(pdf_path):
    """Extract data from Oman Air PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'OMAN AIR')
    extractor.extract_all()
    return extractor.data

def extract_data_qatar(pdf_path):
    """Extract data from Qatar Airways PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'QATAR AIRWAYS')
    extractor.extract_all()
    return extractor.data

def extract_data_srilankan(pdf_path):
    """Extract data from SriLankan Airlines PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'SRILANKAN AIRLINES')
    extractor.extract_gstins()
    extractor.extract_invoice_number([
        r'Serial\s*No\.?[:\s]+([0-9]+)',
        r'Invoice\s*(?:No|Number)[:\s]*([A-Z0-9\-/]+)',
    ])
    extractor.extract_customer_name()
    extractor.extract_date()
    extractor.extract_pnr()
    extractor.extract_route()
    extractor.extract_financial_data_from_tables()
    extractor.extract_financial_data_from_text()
    extractor.apply_post_extraction_logic()
    return extractor.data

def extract_data_turkish(pdf_path):
    """Extract data from Turkish Airlines PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'TURKISH AIRLINES')
    extractor.extract_all()
    return extractor.data

def extract_data_malaysia(pdf_path):
    """Extract data from Malaysia Airlines PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'MALAYSIA AIRLINES')
    extractor.extract_invoice_number([
        r'Invoice\s*No\s*[:\s]*([A-Z0-9]+[/-]\d+[/-]\d+)',
        r'([A-Z]{2}\d{2}[/-]\d+[/-]\d+)',
    ])
    extractor.extract_all()
    return extractor.data

def extract_data_akasa(pdf_path):
    """Extract data from Akasa Air PDF"""
    preprocessor = PDFPreprocessor(pdf_path)
    preprocessor.extract_content()
    content = preprocessor.get_content()
    
    extractor = UnifiedDataExtractor(content, 'AKASA AIR')
    extractor.extract_all()
    return extractor.data

# ================================================================================
# FLASK ROUTES
# ================================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/progress')
def get_progress():
    return jsonify(progress_data)

@app.route('/process', methods=['POST'])
def process_pdfs():
    global progress_data
    
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    airline = request.form.get('airline', 'auto')
    
    if not files:
        return jsonify({'error': 'No files selected'}), 400
    
    # Reset progress
    progress_data = {'current': 0, 'total': len(files), 'status': 'processing', 'message': 'Starting...'}
    
    # Process files
    all_data = []
    
    for idx, file in enumerate(files):
        if file and allowed_file(file.filename):
            progress_data['current'] = idx + 1
            progress_data['message'] = f'Processing {file.filename}'
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Auto-detect airline if needed
                if airline == 'auto':
                    detected_airline = detect_airline(filepath)
                else:
                    detected_airline = airline
                
                # Extract data based on airline
                if detected_airline == 'airindia':
                    extracted_data = extract_data_airindia(filepath)
                elif detected_airline == 'airindiaexpress':
                    extracted_data = extract_data_airindiaexpress(filepath)
                elif detected_airline == 'kuwait':
                    extracted_data = extract_data_kuwait(filepath)
                elif detected_airline == 'oman':
                    extracted_data = extract_data_oman(filepath)
                elif detected_airline == 'qatar':
                    extracted_data = extract_data_qatar(filepath)
                elif detected_airline == 'srilankan':
                    extracted_data = extract_data_srilankan(filepath)
                elif detected_airline == 'turkish':
                    extracted_data = extract_data_turkish(filepath)
                elif detected_airline == 'malaysia':
                    extracted_data = extract_data_malaysia(filepath)
                elif detected_airline == 'akasa':
                    extracted_data = extract_data_akasa(filepath)
                else:  # indigo or default
                    extracted_data = extract_data_from_pdf(filepath)
                
                # Add filename to extracted data
                extracted_data['File Name'] = filename
                
                all_data.append(extracted_data)
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                all_data.append({
                    'Airline': 'ERROR',
                    'Number': filename,
                    'Error': str(e)
                })
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
    
    # Create Excel file
    try:
        df = pd.DataFrame(all_data)
        
        # Reorder columns
        column_order = ['File Name', 'GSTIN', 'GSTIN of Customer', 'Number', 'GSTIN Customer Name', 
                       'Date', 'PNR', 'Taxable Value', 'CGST', 'SGST', 'IGST', 
                       'Total(Incl Taxes)']
        
        for col in column_order:
            if col not in df.columns:
                df[col] = ''
        
        df = df[column_order]
        
        # Save to Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'airline_invoices_{timestamp}.xlsx'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        progress_data['status'] = 'complete'
        progress_data['message'] = 'Processing complete!'
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
        
    except Exception as e:
        progress_data['status'] = 'error'
        progress_data['message'] = f'Error creating Excel: {str(e)}'
        return jsonify({'error': str(e)}), 500

# This is required for Vercel
app = app
