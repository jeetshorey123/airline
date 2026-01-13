from flask import Flask, jsonify
import sys

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'working', 
        'message': 'Minimal Flask app is running',
        'python_version': sys.version
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# Vercel needs this
app = app
