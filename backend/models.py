from datetime import datetime

class Sentence:
    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

class Article:
    def __init__(self, id, title, content, audio_filename, created_at, sentences=None):
        self.id = id
        self.title = title
        self.content = content
        self.audio_filename = audio_filename
        self.created_at = created_at
        self.sentences = sentences or []