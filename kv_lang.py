KV = '''
ScreenManager:
    MainScreen:
    PhotoScreen:
    VideoScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        
        Label:
            text: 'Распознавание номеров'
            font_size: '24sp'
            size_hint_y: 0.2
            color: 0, 0, 0, 1
        
        Label:
            text: 'Система детекции номеров OpenCV + Tesseract ORC '
            text_size: self.width, None
            halign: 'center'
            valign: 'top'
            size_hint_y: 0.15
            color: 0, 0, 0, 1
        
        Button:
            text: '📷 Распознать на фото'
            size_hint_y: 0.15
            background_color: 0.2, 0.6, 0.8, 1
            color: 1, 1, 1, 1
            on_release: app.root.current = 'photo'
        
        Button:
            text: '🎥 Детекция номера на видео'
            size_hint_y: 0.15
            background_color: 0.8, 0.3, 0.2, 1
            color: 1, 1, 1, 1
            on_release: app.root.current = 'video'
        
        Label:
            text: 'Поддерживаемые форматы: JPG, PNG, MP4'
            size_hint_y: 0.1
            color: 0.5, 0.5, 0.5, 1

<PhotoScreen>:
    name: 'photo'
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            Button:
                text: '← Назад'
                size_hint_x: 0.3
                on_release: app.go_to_main()
                background_color: 0.5, 0.5, 0.5, 1
                color: 1, 1, 1, 1
            Label:
                text: 'Распознавание номера на фото'
                font_size: '18sp'
                color: 0, 0, 0, 1
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                spacing: 15
                size_hint_y: None
                height: self.minimum_height
                padding: 10
                
                Button:
                    text: 'Выбрать фото'
                    size_hint_y: None
                    height: 50
                    background_color: 0.2, 0.6, 0.8, 1
                    color: 1, 1, 1, 1
                    on_release: app.select_photo()
                
                Label:
                    id: photo_path
                    text: 'Файл не выбран, повторите попытку'
                    size_hint_y: None
                    height: 30
                    color: 0.5, 0.5, 0.5, 1
                
                ProgressBar:
                    id: progress_bar
                    value: 0
                    size_hint_y: None
                    height: 20
                
                Label:
                    id: progress_label
                    text: '0%'
                    size_hint_y: None
                    height: 30
                    color: 0, 0, 0, 1
                
                Button:
                    id: process_btn
                    text: 'Начать распознавание'
                    size_hint_y: None
                    height: 50
                    disabled: True
                    background_color: 0.2, 0.8, 0.4, 1
                    color: 1, 1, 1, 1
                    on_release: app.start_photo_processing()
                
                Widget:
                    size_hint_y: None
                    height: 220
                    canvas.before:
                        Color:
                            rgba: 0.95, 0.95, 0.95, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [10]
                    
                    BoxLayout:
                        orientation: 'vertical'
                        padding: 10
                        spacing: 5
                        pos: self.parent.pos
                        size: self.parent.size
                        
                        Label:
                            text: 'Результат:'
                            font_size: '16sp'
                            size_hint_y: None
                            height: 30
                            color: 0, 0, 0, 1
                        
                        Label:
                            id: result_text
                            text: 'Результат будет здесь'
                            markup: True
                            text_size: self.width, None
                            valign: 'top'
                            size_hint_y: None
                            height: 180
                            color: 0, 0, 0, 1

<VideoScreen>:
    name: 'video'
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10
        
        BoxLayout:
            size_hint_y: 0.1
            Button:
                text: '← Назад'
                size_hint_x: 0.3
                on_release: app.go_to_main()
                background_color: 0.5, 0.5, 0.5, 1
                color: 1, 1, 1, 1
            Label:
                text: 'Поиск номера на видео'
                font_size: '18sp'
                color: 0, 0, 0, 1
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                spacing: 15
                size_hint_y: None
                height: self.minimum_height
                padding: 10
                
                Button:
                    text: 'Выбирите видео'
                    size_hint_y: None
                    height: 50
                    background_color: 0.8, 0.3, 0.2, 1
                    color: 1, 1, 1, 1
                    on_release: app.select_video()
                
                Label:
                    id: video_path
                    text: 'Файл не выбран'
                    size_hint_y: None
                    height: 30
                    color: 0.5, 0.5, 0.5, 1
                
                ProgressBar:
                    id: video_progress
                    value: 0
                    size_hint_y: None
                    height: 20
                
                Label:
                    id: video_progress_label
                    text: '0%'
                    size_hint_y: None
                    height: 30
                    color: 0, 0, 0, 1
                
                Label:
                    id: frames_label
                    text: 'Обработано кадров: 0'
                    size_hint_y: None
                    height: 30
                    color: 0, 0, 0, 1
                
                Button:
                    id: process_video_btn
                    text: 'Начать поиск'
                    size_hint_y: None
                    height: 50
                    disabled: True
                    background_color: 0.8, 0.5, 0.2, 1
                    color: 1, 1, 1, 1
                    on_release: app.start_video_processing()
                
                Image:
                    id: plate_image
                    size_hint_y: None
                    height: 150
                    allow_stretch: True
                    keep_ratio: True
                
                Label:
                    id: video_result
                    text: 'Здесь будет отображён результат'
                    size_hint_y: None
                    height: 60
                    color: 0, 0, 0, 1
'''