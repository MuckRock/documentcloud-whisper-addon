"""
Upload transcribed audio files to DocumentCloud using Whisper
"""

import requests
import whisper
from documentcloud.addon import AddOn


class Whisper(AddOn):

    def main(self):
        url = self.data["url"]

        with open("audio.mp3", "wb") as audio_file:
            resp = requests.get(url)
            audio_file.write(resp.content)

        model = whisper.load_model("base")
        result = model.transcribe("audio.mp3")

        print(result)

        with open("transcribe.txt", "w+") as file_:
            file_.write(result["text"])
            self.upload_file(file_)
        self.client.documents.upload("transcribe.txt", original_extension="txt")



if __name__ == "__main__":
    Whisper().main()
