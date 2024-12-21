from flask import Flask, render_template, request, redirect, url_for, send_file
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import numpy as np
import os
import cv2
import base64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def save_file(file, filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    return path



def encrypt_image(image, key):
    cipher = AES.new(key, AES.MODE_CBC)

    image_bytes = image.tobytes()

  
    padded_data = pad(image_bytes, AES.block_size)

    encrypted_data = cipher.encrypt(padded_data)
    return cipher.iv, encrypted_data



def decrypt_image(encrypted_data, iv, key, shape):
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)

  
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)

    
    image = np.frombuffer(decrypted_data, dtype=np.float32).reshape(shape)
    return image



@app.route('/')
def home():
    return render_template(
        'index.html',
        image_path=request.args.get('image_path'),
        encrypted_image_path=request.args.get('encrypted_image_path'),
        decrypted_image_path=request.args.get('decrypted_image_path'),
        key_file=request.args.get('key_file'),
    )



@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return "No image file uploaded", 400

    image_file = request.files['image']
    image_path = save_file(image_file, image_file.filename)
    return redirect(url_for('home', image_path=image_path))



@app.route('/encrypt', methods=['POST'])
def encrypt_image_route():
    image_path = request.form['image_path']

    if not image_path:
        return "No image uploaded for encryption!", 400

    
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        return "Error loading the image.", 400

    
    image = image.astype(np.float32) / 255.0

  
    key = get_random_bytes(16)  

    
    iv, encrypted_data = encrypt_image(image, key)

    
    encrypted_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'encrypted.png')
    with open(encrypted_image_path, 'wb') as f:
        f.write(iv + encrypted_data)

    
    key_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'key.txt')
    with open(key_file_path, 'wb') as f:
        f.write(base64.b64encode(key))

    
    shape_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'shape.txt')
    np.savetxt(shape_file_path, image.shape)

    return redirect(
        url_for(
            'home',
            encrypted_image_path=encrypted_image_path,
            key_file=key_file_path,
            shape_file=shape_file_path,
        )
    )


@app.route('/decrypt', methods=['POST'])
def decrypt_image_route():
    if 'image' not in request.files or 'key' not in request.files:
        return "Both image and key are required for decryption!", 400

    image_file = request.files['image']
    key_file = request.files['key']

    
    image_path = save_file(image_file, image_file.filename)
    key_path = save_file(key_file, key_file.filename)

    
    with open(image_path, 'rb') as f:
        iv = f.read(16)  
        encrypted_data = f.read()  

   
    with open(key_path, 'rb') as f:
        key = base64.b64decode(f.read())

    
    shape_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'shape.txt')
    shape = np.loadtxt(shape_file_path, dtype=int)

    
    decrypted_image = decrypt_image(encrypted_data, iv, key, shape)

    
    decrypted_image = np.clip(decrypted_image * 255, 0, 255).astype(np.uint8)


    decrypted_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'decrypted.jpg')
    cv2.imwrite(decrypted_image_path, decrypted_image)  

    return redirect(url_for('home', decrypted_image_path=decrypted_image_path))



@app.route('/download_key/<filename>')
def download_key(filename):
    key_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(key_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
