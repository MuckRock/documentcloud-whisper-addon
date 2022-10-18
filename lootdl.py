""" This file is an All-In-One module for downloading from cloud storage services
Supports share links from Google Drive, Dropbox, MediaFire, and WeTransfer
Does not use any APIs
Thank you to the authors of the following repos:
"gdrivedl" by matthuisman - https://github.com/matthuisman/gdrivedl
"mediafire-dl" by Juvenal-Yescas - https://github.com/Juvenal-Yescas/mediafire-dl
"transferwee" by iamleot - https://github.com/iamleot/transferwee """

import os
import zipfile
from bs4 import BeautifulSoup
import patoolib
import requests
import gdrivedl
import mediafiredl
import wetransferdl
import mediafire_request

# Define urls to filter cloud service
GDRIVE_URL = "drive.google.com"
DROPBOX_URL = "dropbox.com"
MEDIAFIRE_URL = "mediafire.com"
WETRANSFER_URL = "wetransfer.com"


def download_folder(url, output_folder):
    """Google drive folder link url downloader"""
    download = gdrivedl.GDriveDL(quiet=False, overwrite=False, mtimes=False)
    download.process_url(url, output_folder, filename=None)


def download_file(url, output_folder, filename):
    """Google drive file link url downloader"""
    download = gdrivedl.GDriveDL(quiet=False, overwrite=False, mtimes=False)
    download.process_url(url, output_folder, filename)


def get_title(url):
    """Gets file/folder title with requests"""
    reqs = requests.get(url, timeout=5)
    soup = BeautifulSoup(reqs.text, "html.parser")
    for title in soup.find_all("title"):
        return title.get_text()


def get_title_mf(url):
    """Gets mediafire file/folder title with requests"""
    reqs = mediafire_request.get_mediafire(url)
    soup = BeautifulSoup(reqs.text, "html.parser")
    temp_output = str(soup.find("div", {"class": "filename"}).get_text())
    return temp_output


def compression_type(file_name):
    """Detects file compression type"""
    ext = os.path.splitext(file_name)[-1].lower()
    print(ext)
    return ext


def unzip(zipped_file, unzipped_file, directory):
    """Uncompresses files and then deletes compressed folder"""
    if compression_type(zipped_file) == ".zip":
        zip_path = directory + zipped_file
        unzip_path = directory + unzipped_file
        print("--> Extracting to: " + unzip_path)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(unzip_path)
            zip_ref.close()
        os.remove(zip_path)
    if compression_type(zipped_file) == ".rar":
        zip_path = directory + zipped_file
        unzip_path = directory + unzipped_file
        print("---> Extracting to: " + unzip_path)
        patoolib.extract_archive(zip_path, outdir=directory)
        os.remove(zip_path)


def gd_download(url, directory):
    """Download from Google Drive"""
    if "folder" in url:
        output = get_title(url)[:-15]
        output_path = directory + output
        print("---> Downloading to: " + output_path)
        download_folder(url, output_path)
    elif "file" in url:
        temp_output = get_title(url)[:-15]
        output = temp_output.split(".", 1)[0]
        print("---> Downloading to: " + directory + temp_output)
        download_file(url, directory, temp_output)
        unzip(temp_output, output, directory)
    else:
        print("The url: " + url + " is not supported, sorry.")


def db_download(url, directory):
    """Download from Dropbox"""
    url = url[:-1] + "0"
    file_name = get_title(url)[:-21][10:]
    print(file_name)
    suffix1 = file_name.endswith(".zip")
    suffix2 = file_name.endswith(".rar")
    dl_url = url[:-1] + "1"
    filepath = directory + file_name
    print("---> Downloading to: " + filepath)
    output = file_name[:-4]
    headers = {"user-agent": "Wget/1.16 (linux-gnu)"}
    request = requests.get(dl_url, stream=True, headers=headers, timeout=5)
    with open(filepath, "wb") as file:
        for chunk in request.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    if suffix1 or suffix2:
        unzip(file_name, output, directory)


def mf_download(url, directory):
    """Download from MediaFire"""
    zip_name = get_title_mf(url)
    temp_output = directory + zip_name
    print("---> Downloading to: " + temp_output)
    output = zip_name[:-4]
    mediafiredl.download(url, temp_output, quiet=True)
    unzip(zip_name, output, directory)


def wt_download(url, directory):
    """Download from WeTransfer"""
    wetransferdl.download(url, directory, extract=True)


def grab(url, output_path):
    """Detects url cloud service type and downloads it to a specific location"""
    if GDRIVE_URL in url:
        gd_download(url, output_path)
    if DROPBOX_URL in url:
        db_download(url, output_path)
    if MEDIAFIRE_URL in url:
        mf_download(url, output_path)
    if WETRANSFER_URL in url:
        wt_download(url, output_path)
