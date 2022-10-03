"""
Upload transcribed audio files to DocumentCloud using Whisper
"""

import requests
import whisper
from documentcloud.addon import AddOn


def format_timestamp(seconds):
    """Convert seconds in floating point to a string timestamp"""
    seconds = int(seconds)
    return f"{seconds // 60:d}:{seconds % 60:02d}"


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

        print(result)

        with open(title, "w+") as file_:
            for segment in results["segments"]:
                timestamp = format_timestamp(segment["start"])
                file_.write(f"{timestamp}: {segment['text']}\n")
            self.upload_file(file_)

        self.client.documents.upload(title, original_extension="txt")


if __name__ == "__main__":
    Whisper().main()
