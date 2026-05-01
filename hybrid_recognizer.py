import cv2
import numpy as np
import re
import pytesseract
from ultralytics import YOLO

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ALLOWED_RUSSIAN_LETTERS = set("АВЕКМНОРСТУХ")
LATIN_TO_RUSSIAN = {
    'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
    'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
    'X': 'Х', 'Y': 'У'
}
DIGIT_TO_LETTER = {
    '0': 'O', '1': 'I', '2': 'Z', '3': 'E', '4': 'A',
    '5': 'S', '6': 'G', '7': 'T', '8': 'B', '9': 'P'
}
LETTER_TO_DIGIT = {
    'O': '0', 'I': '1', 'Z': '2', 'E': '3', 'A': '4',
    'S': '5', 'G': '6', 'T': '7', 'B': '8', 'P': '9'
}

class HybridPlateRecognizer:
    def __init__(self, use_yolo_fallback=True):
        self.use_yolo_fallback = use_yolo_fallback
        self.yolo_model = None
        if use_yolo_fallback:
            try:
                self.yolo_model = YOLO('yolov8_plate.pt')
            except Exception as e:
                print(f"[YOLO] Ошибка загрузки: {e}")
                self.use_yolo_fallback = False
        self.is_loaded = True

    def _preprocess_image(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        binary = cv2.adaptiveThreshold(blurred, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return closed

    def _find_plate_by_contours(self, img):
        h, w = img.shape[:2]
        roi = img[int(h*0.5):h, :]
        processed = self._preprocess_image(roi)
        contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_score = 0
        print("\n[OpenCV] Поиск по контурам")
        for cnt in contours:
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            if w_box < 80 or h_box < 20 or w_box > 0.8*w or h_box > 0.3*h:
                continue
            aspect = w_box / h_box
            if not (2.0 < aspect < 6.0):
                continue
            area = cv2.contourArea(cnt)
            fill = area / (w_box * h_box) if (w_box * h_box) > 0 else 0
            if fill < 0.4:
                continue
            score = (1.0 - abs(aspect - 4.0)/4.0) * (w_box*h_box/(w*h)) * fill
            if score > best_score:
                best_score = score
                best = (x, y + int(h*0.5), w_box, h_box)
                print(f"  - Кандидат: {best}, aspect={aspect:.2f}, fill={fill:.2f}, score={score:.3f}")
        if best:
            print(f"[OpenCV] Выбран контур: {best}, оценка {best_score:.3f}")
            return best
        print("[OpenCV] Контуры не подошли.")
        return None

    def _find_plate_by_morphology(self, img):
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_x = cv2.convertScaleAbs(sobel_x)
        _, edge_bin = cv2.threshold(sobel_x, 50, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edge_bin, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_area = 0
        print("\n[OpenCV] Поиск по морфологии (вертикальные градиенты)")
        for cnt in contours:
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            if w_box < 100 or h_box < 20 or w_box > 0.8*w or h_box > 0.2*h:
                continue
            aspect = w_box / h_box
            if 2.5 < aspect < 6.0:
                area = w_box * h_box
                if area > best_area:
                    best_area = area
                    best = (x, y, w_box, h_box)
                    print(f"  - Кандидат: {best}, aspect={aspect:.2f}, area={area}")
        if best:
            print(f"[OpenCV] Выбрана область: {best}")
            return best
        print("[OpenCV] По морфологии ничего не найдено.")
        return None

    def detect_plate_opencv(self, img):
        print("\n=== OpenCV: начало детекции ===")
        plate = self._find_plate_by_contours(img)
        if plate is None:
            plate = self._find_plate_by_morphology(img)
        if plate:
            print(f"[OpenCV] Финал: область {plate}")
            return plate
        print("[OpenCV] Не удалось найти номер.")
        return None

    def _preprocess_simple(self, plate_img):
        h, w = plate_img.shape[:2]
        scale = max(600 / w, 3.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        upscaled = cv2.resize(plate_img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(binary) > 127:
            binary = cv2.bitwise_not(binary)
        return binary

    def _preprocess_advanced(self, plate_img):
        h, w = plate_img.shape[:2]
        scale = max(400 / w, 2.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        upscaled = cv2.resize(plate_img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
        denoised = cv2.medianBlur(gray, 3)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrasted = clahe.apply(denoised)
        _, binary = cv2.threshold(contrasted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(binary) > 127:
            binary = cv2.bitwise_not(binary)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        return cleaned

    def _normalize_strict(self, raw_text):
        if not raw_text:
            return None
        clean = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        match = re.search(r'([A-Z])(\d{3})([A-Z]{2})', clean)
        if not match:
            return None
        letter1, digits, letters2 = match.groups()
        rus_l1 = LATIN_TO_RUSSIAN.get(letter1, letter1)
        rus_l2 = ''.join(LATIN_TO_RUSSIAN.get(ch, ch) for ch in letters2)
        if (rus_l1 in ALLOWED_RUSSIAN_LETTERS and
            all(ch in ALLOWED_RUSSIAN_LETTERS for ch in rus_l2)):
            return f"{rus_l1}{digits}{rus_l2}"
        return None

    def _normalize_fuzzy(self, raw_text):
        if not raw_text:
            return None
        clean = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        for length in (6, 7, 8):
            for start in range(len(clean) - length + 1):
                cand = clean[start:start+length]
                if len(cand) < 6:
                    continue
                letter1 = cand[0]
                digits_part = cand[1:4]
                letters_part = cand[4:]
                fixed_letter1 = DIGIT_TO_LETTER.get(letter1, letter1)
                fixed_digits = ''.join(LETTER_TO_DIGIT.get(ch, ch) for ch in digits_part)
                fixed_letters = ''.join(DIGIT_TO_LETTER.get(ch, ch) for ch in letters_part)[:2]
                if (fixed_letter1.isalpha() and fixed_digits.isdigit() and len(fixed_digits)==3 and
                    fixed_letters.isalpha() and len(fixed_letters)==2):
                    rus_l1 = LATIN_TO_RUSSIAN.get(fixed_letter1, fixed_letter1)
                    rus_l2 = ''.join(LATIN_TO_RUSSIAN.get(ch, ch) for ch in fixed_letters)
                    if (rus_l1 in ALLOWED_RUSSIAN_LETTERS and
                        all(ch in ALLOWED_RUSSIAN_LETTERS for ch in rus_l2)):
                        return f"{rus_l1}{fixed_digits}{rus_l2}"
        return None

    def recognize_plate_text(self, plate_img):
        preprocessors = [
            ("simple", self._preprocess_simple),
            ("advanced", self._preprocess_advanced)
        ]
        configs = [
            r'--oem 3 --psm 8',
            r'--oem 3 --psm 7',
            r'--oem 3 --psm 13'
        ]
        languages = ['eng', 'rus+eng']
        normalizers = [
            ("strict", self._normalize_strict),
            ("fuzzy", self._normalize_fuzzy)
        ]

        for prep_name, prep_func in preprocessors:
            processed = prep_func(plate_img)
            for lang in languages:
                for idx, config in enumerate(configs):
                    try:
                        raw = pytesseract.image_to_string(processed, lang=lang, config=config)
                        raw = raw.strip()
                        print(f"[OCR] {prep_name}/{lang}/psm{config[-1]}: '{raw}'")
                        for norm_name, norm_func in normalizers:
                            result = norm_func(raw)
                            if result:
                                print(f"[OCR] УСПЕХ: {result} (метод: {prep_name}+{norm_name})")
                                return result
                    except Exception as e:
                        print(f"[OCR] Ошибка: {e}")
        return None

    def detect_and_recognize(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None, "Не удалось загрузить изображение"

        plate_box = self.detect_plate_opencv(img)
        if plate_box:
            x, y, w, h = plate_box
            x = max(0, x - int(w*0.1))
            y = max(0, y - int(h*0.1))
            w = min(img.shape[1] - x, int(w*1.2))
            h = min(img.shape[0] - y, int(h*1.2))
            plate_roi = img[y:y+h, x:x+w]
            plate_text = self.recognize_plate_text(plate_roi)
            if plate_text:
                return {'plate': plate_text, 'confidence': 0.85, 'detection_conf': 0.7, 'method': 'OpenCV'}, None
            print("[OpenCV] Не удалось распознать текст.")
        else:
            print("[OpenCV] Номер не найден.")

        if self.use_yolo_fallback and self.yolo_model:
            print("\n=== YOLO: резервная детекция ===")
            try:
                results = self.yolo_model(img, conf=0.25)
                height, width = img.shape[:2]
                for result in results:
                    if result.boxes is not None:
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            conf = float(box.conf[0])
                            x1, y1 = max(0, x1), max(0, y1)
                            x2, y2 = min(width, x2), min(height, y2)
                            plate_roi = img[y1:y2, x1:x2]
                            plate_text = self.recognize_plate_text(plate_roi)
                            if plate_text:
                                return {'plate': plate_text, 'confidence': 0.9, 'detection_conf': conf, 'method': 'YOLO'}, None
                print("[YOLO] Номер не распознан.")
            except Exception as e:
                print(f"[YOLO] Ошибка: {e}")

        return None, "Номер не найден"

    def detect_plate_roi(self, frame):
        plate_box = self.detect_plate_opencv(frame)
        if plate_box:
            x, y, w, h = plate_box
            x = max(0, x - int(w*0.1))
            y = max(0, y - int(h*0.1))
            w = min(frame.shape[1] - x, int(w*1.2))
            h = min(frame.shape[0] - y, int(h*1.2))
            roi = frame[y:y+h, x:x+w]
            if roi.size == 0:
                return None
            if len(roi.shape) == 2:
                roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            return roi
        return None