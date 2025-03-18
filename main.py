"""
Upload transcribed audio files to DocumentCloud using Whisper
"""
import os
import json
import shutil
import sys
from subprocess import call, CalledProcessError
from urllib.parse import urlparse

import requests
import whisper
from documentcloud.addon import AddOn
from documentcloud.exceptions import APIError

from clouddl import grab
from yt_dlp import YoutubeDL

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
    """Whisper Add-On class"""

    def check_project(self, project_id):
        """Checks whether we can retrieve the project, handles the error right away if not"""
        try:
            self.client.projects.get(project_id)
        except APIError:
            self.set_message("The project you provided does not exist, try again.")
            sys.exit(0)
        except ValueError:
            pass

    def check_permissions(self):
        """The user must be a verified journalist to upload a document"""
        self.set_message("Checking permissions...")
        user = self.client.users.get("me")
        # pylint: disable=no-member
        if not user.verified_journalist:
            self.set_message(
                "You need to be verified to use this add-on. Please verify your "
                "account here: https://airtable.com/shrZrgdmuOwW0ZLPM"
            )
            sys.exit()

    def fetch_files(self, url):
        """Fetch the files from either a cloud share link or any public URL"""

        self.set_message("Downloading the files...")

        os.makedirs(os.path.dirname("./out/"), exist_ok=True)
        downloaded = grab(url, "./out/")

        if "youtube.com" in url or "youtu.be" in url:
            request_check = requests.get(url, timeout=15)
            if "Video unavailable" in request_check.text:
                self.set_message("Not a valid YouTube video URL, please try again")
                sys.exit(1)
            else:
                """self.set_message("Unfortunately, due to new bot detection policies, YouTube videos are no longer supported in this Add-On.")
                sys.exit(0)
                """
                os.chdir("./out/")
                ydl_opts = {
                    "user-agent": "Transcribe Audio Add-On",
                    "referer": "https://documentcloud.org",
                    "quiet": True,
                    "noplaylist": True,
                    "format": "m4a/bestaudio/best",
                    "postprocessors": [
                        {  # Extract audio using ffmpeg
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "m4a",
                        }
                    ],
                }
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                os.chdir("..")
                downloaded = True
        if "facebook.com" in url:
            os.chdir("./out/")
            ydl_opts = {
                "quiet": True,
                "noplaylist": True,
                "format": "m4a/bestaudio/best",
                "postprocessors": [
                    {  # Extract audio using ffmpeg
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                    }
                ],
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            os.chdir("..")
            downloaded = True
        if not downloaded:
            parsed_url = urlparse(url)
            basename = os.path.basename(parsed_url.path)
            title, ext = os.path.splitext(basename)
            if not title:
                title = "audio_transcription"
            if not ext:
                ext = "mp3"
            with requests.get(url, stream=True, timeout=15) as resp:
                resp.raise_for_status()
                with open(f"./out/{title}.{ext}", "wb") as audio_file:
                    for chunk in resp.iter_content(chunk_size=8192):
                        audio_file.write(chunk)

    def main(self):
        """Pulls the variables from UI, checks permissions, and runs the transcription"""
        url = self.data["url"]
        project_id = self.data.get("project_id")
        access_level = self.data["access_level"]
        if project_id is not None:
            kwargs = {"project": project_id}
        else:
            kwargs = {}
        model = self.data.get("model")

        self.check_permissions()
        self.check_project(project_id)
        self.fetch_files(url)

        self.set_message("Preparing for transcription...")

        model = whisper.load_model(model)  # pylint: disable=no-member

        errors = 0
        successes = 0
        for current_path, _folders, files in os.walk("./out/"):
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

                with open(f"{basename}.txt", "w+", encoding="utf-8") as file_:
                    format_segments(result, file_)
                try:
                    self.client.documents.upload(
                        f"{basename}.txt",
                        original_extension="txt",
                        access=access_level,
                        **kwargs,
                    )
                except APIError as e:
                    error_data = json.loads(e.response)
                    if "projects" in error_data:
                        self.set_message(
                            "Please check that you provided either a"
                            "valid project ID or left it completely blank. Try again."
                        )
                        sys.exit(0)
                    else:
                        self.set_message(
                            "API error reached, contact info@documentcloud.org for support"
                        )
                        print(e)
                        sys.exit(1)

                successes += 1

        sfiles = "file" if successes == 1 else "files"
        efiles = "file" if errors == 1 else "files"
        self.set_message(f"Transcribed {successes} {sfiles}, skipped {errors} {efiles}")
        shutil.rmtree("./out/", ignore_errors=False, onerror=None)


if __name__ == "__main__":
    Whisper().main()
