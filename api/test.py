from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({'status': 'working', 'message': 'Minimal Flask app is running'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# Vercel handler
handler = app
