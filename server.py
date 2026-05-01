from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import re
from hybrid_recognizer import HybridPlateRecognizer

app = Flask(__name__)
recognizer = HybridPlateRecognizer(use_yolo_fallback=True)

@app.route('/recognize', methods=['POST'])
def recognize():
    data = request.json
    image_data = base64.b64decode(data['image'])
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    # Сохраняем во временный файл (удобнее для существующей функции)
    temp_path = "temp_plate.jpg"
    cv2.imwrite(temp_path, img)
    result, error = recognizer.detect_and_recognize(temp_path)
    if result:
        return jsonify({'plate': result['plate']})
    else:
        return jsonify({'error': error or 'Номер не найден'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)