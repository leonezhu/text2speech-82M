from datetime import datetime

class Article:
    def __init__(self, id, title, content, audio_filename, created_at):
        self.id = id
        self.title = title
        self.content = content
        self.audio_filename = audio_filename
        self.created_at = created_at