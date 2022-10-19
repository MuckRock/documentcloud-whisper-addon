"""
Upload transcribed audio files to DocumentCloud using Whisper
"""

import os
import shutil
import sys
from urllib.parse import urlparse

import requests
import whisper
from documentcloud.addon import AddOn

import lootdl
from lootdl import DROPBOX_URL, GDRIVE_URL, MEDIAFIRE_URL, WETRANSFER_URL

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
            start = segment["start"]
            text = segment["text"]
        else:
            text += segment["text"]

    # write out the final segment
    timestamp = format_timestamp(segment["start"])
    file.write(f"{timestamp}: {text}\n\n")


class Whisper(AddOn):
    def fetch_files(self, url):
        """Fetch the files from either a cloud share link or any public URL"""

        self.set_message("Downloading the files...")

        os.makedirs(os.path.dirname("./out/"), exist_ok=True)
        cloud_urls = [DROPBOX_URL, GDRIVE_URL, MEDIAFIRE_URL, WETRANSFER_URL]
        if any(cloud_url in url for cloud_url in cloud_urls):
            # surpress output during lootdl download to avoid leaking
            # private information
            stdout = sys.stdout
            sys.stdout = open(os.devnull, "w")
            lootdl.grab(url, "./out/")
            # restore stdout
            sys.stdout = stdout
        else:
            parsed_url = urlparse(url)
            basename = os.path.basename(parsed_url.path)
            title, ext = os.path.splitext(basename)
            if not title:
                title = "audio_transcription"
            if not ext:
                ext = "mp3"
            with requests.get(url, stream=True) as resp:
                resp.raise_for_status()
                with open(f"./out/{title}.{ext}", "wb") as audio_file:
                    for chunk in resp.iter_content(chunk_size=8192):
                        audio_file.write(chunk)

    def main(self):
        url = self.data["url"]
        # we default to the base model - this could be made configurable
        # but decided to keep things simple for now
        model = "base"

        self.fetch_files(url)

        self.set_message("Preparing for transcription...")

        model = whisper.load_model(model)

        errors = 0
        successes = 0
        for current_path, folders, files in os.walk("./out/"):
            for file_name in files:
                file_name = os.path.join(current_path, file_name)
                basename = os.path.basename(file_name)
                self.set_message(f"Transcribing {basename}...")
                try:
                    result = model.transcribe(file_name)
                except RuntimeError:
                    # This probably means it was not an audio file
                    errors += 1
                    continue

                with open(f"{basename}.txt", "w+") as file_:
                    format_segments(result, file_)

                self.client.documents.upload(
                    f"{basename}.txt", original_extension="txt"
                )
                successes += 1

        sfiles = "file" if successes == 1 else "files"
        efiles = "file" if errors == 1 else "files"
        self.set_message(f"Transcribed {successes} {sfiles}, skipped {errors} {efiles}")
        shutil.rmtree("./out/", ignore_errors=False, onerror=None)


if __name__ == "__main__":
    Whisper().main()
