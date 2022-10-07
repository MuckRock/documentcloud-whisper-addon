"""
Upload transcribed audio files to DocumentCloud using Whisper
"""

import requests
import whisper
from documentcloud.addon import AddOn

MIN_WORDS = 8

def format_timestamp(seconds):
    """Convert seconds in floating point to a string timestamp"""
    seconds = int(seconds)
    return f"{seconds // 60:d}:{seconds % 60:02d}"


def format_segments(result, file):
    """
    Re-format Whisper segments

    Whisper's segments can be overly short, so we make sure they are at least
    complete sentences of a minimum length by combining them.
    """
    start = 0
    text = ""
    for segment in result["segments"]:
        # if the text is at the end of a sentence and is at least MIN_WORDS
        # words long, then write out the segment and start a new one
        if text.endswith((".", "?", "!")) and len(text.split()) >= MIN_WORDS:
            timestamp = format_timestamp(start)
            file.write(f"{timestamp}: {text}\n\n")
            start = s["start"]
            text = s["text"]
        else:
            text += s["text"]

    # write out the final segment
    timestamp = format_timestamp(s["start"])
    file.write(f"{timestamp}: {text}\n\n")
 


class Whisper(AddOn):
    def main(self):
        url = self.data["url"]
        title = self.data["title"]
        model = self.data.get("model") or "base"
        title = f"{title}.txt"

        with open("audio.mp3", "wb") as audio_file:
            resp = requests.get(url)
            audio_file.write(resp.content)

        model = whisper.load_model(model)
        result = model.transcribe("audio.mp3")

        with open(title, "w+") as file_:
            format_segments(result, file_)
            self.upload_file(file_)

        self.client.documents.upload(title, original_extension="txt")


if __name__ == "__main__":
    Whisper().main()
