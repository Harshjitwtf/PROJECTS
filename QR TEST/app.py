import re
import requests
from pyzbar.pyzbar import decode
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os

PHISHING_KEYWORDS = [
    "login", "signin", "verify", "account", "update", "secure", "banking",
    "free", "gift", "prize", "win", "alert", "confirm", "support"
]

SUSPICIOUS_TLDS = [".tk", ".ml", ".ga", ".cf", ".gq"]

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './temp'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def extract_url_from_qr(image_path):
    try:
        decoded_objects = decode(Image.open(image_path))
        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                return obj.data.decode('utf-8')
        return None
    except Exception as e:
        return None

def check_suspicious_patterns(url):
    suspicious_count = 0
    
    if any(keyword in url.lower() for keyword in PHISHING_KEYWORDS):
        suspicious_count += 1
    
    if len(url) > 75:
        suspicious_count += 1
    
    if len(re.findall(r"[._\-@]", url)) > 4:
        suspicious_count += 1

    if any(url.endswith(tld) for tld in SUSPICIOUS_TLDS):
        suspicious_count += 1

    return suspicious_count

def validate_url(url):
    try:
        response = requests.get(url, timeout=5)
        if len(response.history) > 3:
            return False
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.RequestException:
        return False

def identify_phishing_link(url):
    suspicious_count = check_suspicious_patterns(url)
    is_valid = validate_url(url)

    result = {
        "url": url,
        "suspicious_patterns": suspicious_count,
        "is_reachable": is_valid,
        "is_phishing": suspicious_count >= 2 or not is_valid
    }

    return result

@app.route('/')
def home():
    return render_template('index.html', result=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('home', result={"error": "No file part"}))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('home', result={"error": "No selected file"}))

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        url = extract_url_from_qr(file_path)

        if not url:
            return render_template('index.html', result={"error": "No URL found in the QR code"})

        result = identify_phishing_link(url)
        
        # Pass the file name to render the image on the page
        file_url = url_for('uploaded_file', filename=file.filename)
        return render_template('index.html', result=result, qr_image=file_url)

@app.route('/temp/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
