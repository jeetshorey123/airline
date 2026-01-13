from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import time

# Get absolute paths for Vercel
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(os.path.dirname(basedir), 'templates')

# Fallback for different environments
if not os.path.exists(template_dir):
    template_dir = os.path.join(basedir, '..', 'templates')
    template_dir = os.path.abspath(template_dir)

app = Flask(__name__, template_folder=template_dir)
CORS(app)

# Global progress tracking
progress_data = {'current': 0, 'total': 0, 'status': 'idle', 'message': ''}

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

def ensure_directories():
    """Ensure upload and output directories exist"""
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    except Exception as e:
        print(f"Directory creation error: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# LAZY IMPORTS - Only import heavy libraries when needed
def get_pdf_libraries():
    """Lazy import of heavy PDF libraries"""
    import pdfplumber
    import pandas as pd
    import re
    return pdfplumber, pd, re

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'template_dir': template_dir,
        'template_exists': os.path.exists(template_dir),
        'basedir': basedir
    }), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/progress')
def get_progress():
    return jsonify(progress_data)

@app.route('/process', methods=['POST'])
def process_pdfs():
    global progress_data
    
    ensure_directories()
    
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files[]')
    airline = request.form.get('airline', 'auto')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Reset progress
    progress_data = {'current': 0, 'total': len(files), 'status': 'processing', 'message': 'Starting...'}
    
    # Import heavy libraries only when processing
    try:
        pdfplumber, pd, re = get_pdf_libraries()
    except Exception as e:
        return jsonify({'error': f'Failed to load PDF libraries: {str(e)}'}), 500
    
    # Import the full extraction logic here
    from app import extract_data_from_pdf, detect_airline
    from app import extract_data_airindia, extract_data_airindiaexpress
    from app import extract_data_kuwait, extract_data_oman, extract_data_qatar
    from app import extract_data_srilankan, extract_data_turkish
    from app import extract_data_malaysia, extract_data_akasa
    
    all_data = []
    
    for idx, file in enumerate(files):
        if file and allowed_file(file.filename):
            progress_data['current'] = idx + 1
            progress_data['message'] = f'Processing {file.filename}'
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                if airline == 'auto':
                    detected_airline = detect_airline(filepath)
                else:
                    detected_airline = airline
                
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
                else:
                    extracted_data = extract_data_from_pdf(filepath)
                
                extracted_data['File Name'] = filename
                all_data.append(extracted_data)
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                all_data.append({
                    'Airline': 'ERROR',
                    'Number': filename,
                    'Error': str(e)
                })
            
            try:
                os.remove(filepath)
            except:
                pass
    
    try:
        df = pd.DataFrame(all_data)
        
        column_order = ['File Name', 'GSTIN', 'GSTIN of Customer', 'Number', 'GSTIN Customer Name', 
                       'Date', 'PNR', 'Taxable Value', 'CGST', 'SGST', 'IGST', 
                       'Total(Incl Taxes)']
        
        for col in column_order:
            if col not in df.columns:
                df[col] = ''
        
        df = df[column_order]
        
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

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({'error': 'An error occurred', 'message': str(error)}), 500

# Vercel handler
handler = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
