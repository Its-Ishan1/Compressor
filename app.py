# app.py
import os
import io
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from avif_handler import process_image

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

@app.route('/compress', methods=['POST'])
def compress_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image field in the request"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Read image data
        input_data = image_file.read()
        
        # Process image with AUTOMATIC forensic-aware settings
        compressed_bytes = process_image(input_data)
        
        # Save to memory and send
        output = io.BytesIO(compressed_bytes)
        output.seek(0)
        
        filename = os.path.splitext(image_file.filename)[0] + '.avif'
        
        return send_file(
            output,
            mimetype='image/avif',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/thumbnail', methods=['POST'])
def thumbnail_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image"}), 400
    
    image_file = request.files['image']
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_file.read()))
        
        # Convert to RGB for JPEG
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        elif img.mode == "RGBA":
            # Paste on white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
            
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=70)
        output.seek(0)
        
        return send_file(output, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('frontend', path)

if __name__ == '__main__':
    # Using port 5001 for development
    app.run(debug=True, port=5001)
