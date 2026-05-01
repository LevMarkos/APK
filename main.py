print("=== Запуск приложения ===")

import threading
import traceback
import cv2
import tempfile
import os
import base64
import requests
from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.graphics.texture import Texture

from kv_lang import KV
from screens import MainScreen, PhotoScreen, VideoScreen
from hybrid_recognizer import HybridPlateRecognizer  # Нужен только для видео (detect_plate_roi)
from video_processor import VideoProcessor

if platform != 'android':
    Window.size = (400, 700)
    Window.clearcolor = (1, 1, 1, 1)

recognizer = None  # Будет инициализирован для видео (detect_plate_roi)

class LicensePlateApp(App):
    photo_path = StringProperty('')
    video_path = StringProperty('')
    self.server_url = 'http://192.168.0.106:5000/recognize'

    def build(self):
        global recognizer
        root = Builder.load_string(KV)

        def init_recognizer():
            global recognizer
            # Для видео нужен только детектор (без распознавания текста)
            recognizer = HybridPlateRecognizer(use_yolo_fallback=True)
            if recognizer.is_loaded:
                print("=" * 50)
                print("Система готова (детекция для видео)")
                print("=" * 50)

        threading.Thread(target=init_recognizer, daemon=True).start()
        return root

    def go_to_main(self):
        self.root.current = 'main'

    # ---------- Фото (отправка на сервер) ----------
    def select_photo(self):
        content = FileChooserListView(filters=['*.jpg', '*.jpeg', '*.png'])
        popup = Popup(title='Выберите фото', content=content, size_hint=(0.9, 0.9))

        def on_selection(instance, selection, touch=None):
            if selection:
                self.photo_path = selection[0]
                self.root.get_screen('photo').ids.photo_path.text = f'Выбран: {selection[0].split("/")[-1]}'
                self.root.get_screen('photo').ids.process_btn.disabled = False
                popup.dismiss()

        content.bind(on_submit=on_selection)
        popup.open()

    def start_photo_processing(self):
        if not self.photo_path:
            self.root.get_screen('photo').ids.result_text.text = "[color=FF0000]Ошибка: Файл не выбран[/color]"
            return
        # Для фото не нужен локальный recognizer, сразу отправляем на сервер
        self.root.get_screen('photo').ids.process_btn.disabled = True
        self.root.get_screen('photo').ids.progress_label.text = "Отправка на сервер..."
        self.root.get_screen('photo').ids.progress_bar.value = 0.3
        threading.Thread(target=self._process_photo_server, daemon=True).start()

    def _process_photo_server(self):
        try:
            Clock.schedule_once(lambda dt: self._update_photo_progress(0.6, "Ожидание ответа..."))
            with open(self.photo_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
            response = requests.post(self.server_url, json={'image': img_base64}, timeout=15)
            Clock.schedule_once(lambda dt: self._update_photo_progress(1.0, "Готово!"))
            if response.status_code == 200:
                plate = response.json().get('plate', '')
                res_text = f"[b]Распознанный номер:[/b] {plate}"
            else:
                error_msg = response.json().get('error', 'Неизвестная ошибка')
                res_text = f"[color=FF0000]Ошибка сервера: {error_msg}[/color]"
        except requests.exceptions.ConnectionError:
            res_text = "[color=FF0000]Не удалось подключиться к серверу.\nПроверьте IP и запущен ли сервер.[/color]"
        except Exception as e:
            res_text = f"[color=FF0000]Ошибка: {str(e)}[/color]"
            traceback.print_exc()
        Clock.schedule_once(lambda dt: self._finish_photo_processing(res_text))

    def _update_photo_progress(self, value, text):
        screen = self.root.get_screen('photo')
        screen.ids.progress_bar.value = value
        screen.ids.progress_label.text = text

    def _finish_photo_processing(self, result_text):
        screen = self.root.get_screen('photo')
        screen.ids.process_btn.disabled = False
        screen.ids.result_text.text = result_text
        Clock.schedule_once(lambda dt: setattr(screen.ids.progress_bar, 'value', 0), 2)

    # ---------- Видео (без изменений, как в вашем рабочем коде) ----------
    def select_video(self):
        content = FileChooserListView(filters=['*.mp4'])
        popup = Popup(title='Выберите видео (MP4)', content=content, size_hint=(0.9, 0.9))

        def on_selection(instance, selection, touch=None):
            if selection:
                self.video_path = selection[0]
                self.root.get_screen('video').ids.video_path.text = f'Выбран: {selection[0].split("/")[-1]}'
                self.root.get_screen('video').ids.process_video_btn.disabled = False
                popup.dismiss()

        content.bind(on_submit=on_selection)
        popup.open()

    def start_video_processing(self):
        if not self.video_path:
            self.root.get_screen('video').ids.video_result.text = "[color=FF0000]Ошибка: Файл не выбран[/color]"
            return
        global recognizer
        if recognizer is None or not recognizer.is_loaded:
            self.root.get_screen('video').ids.video_result.text = "[color=FF0000]Модели загружаются...[/color]"
            return
        self.video_processor = VideoProcessor(recognizer)
        screen = self.root.get_screen('video')
        screen.ids.process_video_btn.disabled = True
        screen.ids.video_progress.value = 0
        screen.ids.video_progress_label.text = "0%"
        screen.ids.frames_label.text = "Обработано кадров: 0"
        screen.ids.video_result.text = "Обработка видео... (найденные номера будут отображаться выше)"
        screen.ids.plate_image.source = ""
        threading.Thread(target=self._process_video, daemon=True).start()

    def _process_video(self):
        def on_progress(percent, processed, total):
            Clock.schedule_once(lambda dt: self._update_video_progress_ui(percent, processed, total))

        def on_plate_roi(roi):
            if roi is None or roi.size == 0:
                return
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                cv2.imwrite(temp_path, roi)
                img_widget = self.root.get_screen('video').ids.plate_image
                Clock.schedule_once(lambda dt: setattr(img_widget, 'source', temp_path))
                Clock.schedule_once(lambda dt: os.unlink(temp_path), 2)
            except Exception as e:
                print(f"Ошибка сохранения ROI: {e}")

        self.video_processor.process_video(
            self.video_path,
            frame_step=5,
            show_preview=False,
            progress_callback=on_progress,
            plate_roi_callback=on_plate_roi
        )
        Clock.schedule_once(lambda dt: setattr(self.root.get_screen('video').ids.process_video_btn, 'disabled', False))

    def _update_video_progress_ui(self, percent, processed, total):
        screen = self.root.get_screen('video')
        screen.ids.video_progress.value = percent / 100
        screen.ids.video_progress_label.text = f"{percent}%"
        screen.ids.frames_label.text = f"Обработано кадров: {processed}"
        if percent >= 100:
            screen.ids.process_video_btn.disabled = False
            screen.ids.video_result.text = "[color=00AA00]Обработка завершена[/color]"

if __name__ == '__main__':
    try:
        LicensePlateApp().run()
    except Exception as e:
        print("=" * 50)
        print("ОШИБКА:")
        traceback.print_exc()
        print("=" * 50)
        input("Нажмите Enter для выхода...")