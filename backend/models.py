from datetime import datetime

class Sentence:
    def __init__(self, text, start_time, end_time, language=None):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
        self.language = language

class Article:
    def __init__(self, id, title, content, audio_filename, created_at, language_versions=None):
        self.id = id
        self.title = title
        self.content = content
        self.audio_filename = audio_filename
        self.created_at = created_at
        # 存储不同语言版本的信息，格式：{"zh": {"audio_filename": "xxx.wav", "sentences": []}, "en": {...}}
        self.language_versions = language_versions or {}