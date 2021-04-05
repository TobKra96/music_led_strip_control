
class AudioDevice:
    def __init__(self, id, name, defaultSampleRate):
        self.id = id
        self.name = name
        self.defaultSampleRate = defaultSampleRate

    def ToString(self):
        return f"{self.id} - {self.name} - {self.defaultSampleRate}"
