import cv2

class VideoProcessor:
    def __init__(self, recognizer):
        self.recognizer = recognizer
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def process_video(self, video_path, frame_step=5, show_preview=False,
                      progress_callback=None, plate_roi_callback=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            if progress_callback:
                progress_callback(-1, 0, 0)
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        processed_frames = 0
        expected_total = total_frames // frame_step if total_frames else 0
        self.stop_flag = False

        while True:
            if self.stop_flag:
                break
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1

            if frame_count % frame_step != 0:
                continue

            processed_frames += 1
            percent = int(processed_frames * 100 / expected_total) if expected_total else 0
            if progress_callback:
                progress_callback(percent, processed_frames, expected_total)

            roi = self.recognizer.detect_plate_roi(frame)
            if roi is not None and plate_roi_callback:
                plate_roi_callback(roi)

        cap.release()
        if progress_callback:
            progress_callback(100, processed_frames, expected_total)