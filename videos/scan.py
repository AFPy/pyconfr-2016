"""La vidéo DRF c'est pas un atelier. C'est pas Xavier1.
"""

from shlex import quote
import re
from urllib.parse import quote
import requests
from pymediainfo import MediaInfo
from pathlib import Path
from datetime import datetime
import json
import sys
from string import ascii_letters

PYVIDEO_CLONE = Path("~/clones/data/").expanduser()
DL_DIR = Path("~/Downloads/pycon-fr-16/").expanduser()


def normalize(title):
    title = (
        title.replace("Devpy", "Devpi")
        .replace("and", "et")
        .lower()
        .replace("s", "")
        .replace("authe", "aute")
    )
    return "".join(c for c in title.replace("&amp;", "") if c in ascii_letters)


def safe_path(title):
    return title.replace("/", "-").replace(" ", "-")


def output_json(ytid, from_website, from_pyvideo, from_dl_afpy_org):
    if not from_pyvideo:
        print(normalize(from_website["title"]), "not found in pyvideo")
    title = from_pyvideo["title"] if from_pyvideo else from_website["title"]
    description = (
        from_pyvideo["description"] if from_pyvideo else from_website["description"]
    )
    speakers = (
        from_pyvideo["speakers"]
        if from_pyvideo
        else [from_website["properties"]["ryf3vyHJx"]]
    )
    dl_url = "https://dl.afpy.org/pycon-fr-16/" + quote(from_dl_afpy_org["file"].name)
    response = requests.head(dl_url)
    response.raise_for_status()
    out = {
        "description": description,
        "recorded": datetime.fromtimestamp(from_website["date"] // 1000).strftime(
            "%Y-%m-%d"
        ),
        "language": from_pyvideo["language"] if from_pyvideo else "fra",
        "duration": from_dl_afpy_org["duration"],
        "related_urls": [
            {
                "label": "Conference schedule",
                "url": "https://www.pycon.fr/2016/pages/programme.html",
            },
            {
                "label": "talk slides",
                "url": "https://pycon.fr/2016/videos/" + from_website["htmlfile"],
            },
        ],
        "speakers": speakers,
        "thumbnail_url": f"https://i.ytimg.com/vi/{ytid}/maxresdefault.jpg",
        "title": title,
        "videos": [
            {"type": "youtube", "url": "https://www.youtube.com/watch?v=" + ytid},
            {
                "type": from_dl_afpy_org["file"].suffix.strip("."),
                "url": dl_url,
                "size": from_dl_afpy_org["file_size"],
            },
        ],
    }
    if from_pyvideo:
        path = from_pyvideo["path"]
    else:
        path = (
            PYVIDEO_CLONE
            / "pycon-fr-2016"
            / "videos"
            / (safe_path(from_website["title"]) + ".json")
        )

    path.write_text(json.dumps(out, indent=2) + "\n")


def merge(ytids, from_website, from_pyvideo, from_dl_afpy_org):
    for title in from_website.keys():
        ytid = ytids.pop(title)
        website = from_website[title]
        pyvideo = from_pyvideo.pop(title, None)
        dl_afpy_org = from_dl_afpy_org.pop(title)
        output_json(ytid, website, pyvideo, dl_afpy_org)
    for ytid in ytids:
        print("Unmerged ytids", ytid)
    for pyvideo in from_pyvideo:
        print("Unmerge pyvideo", pyvideo, from_pyvideo[pyvideo]["path"])
    for dl_afpy_org in from_pyvideo:
        print("Unmerge from dl.afpy.org", dl_afpy_org)


def main():
    ytids = {}
    from_website = {}
    from_pyvideo = {}
    from_dl_afpy_org = {}

    for file in DL_DIR.glob("*.*"):
        info = MediaInfo.parse(str(file))
        video_info = info.video_tracks[0]
        general_info = info.general_tracks[0]
        from_dl_afpy_org[normalize(file.stem)] = {
            "file": file,
            "duration": int(float(video_info.duration)),
            "file_size": general_info.file_size,
        }

    for line in Path("new-ids").read_text(encoding="utf-8").splitlines():
        ytid, title = line.split(" ", maxsplit=1)
        title = title.strip()
        ytids[normalize(title)] = ytid

    htmls = {}
    for file in Path(".").glob("*.html"):
        # ./memory-safety-with-rust.html:    $http.get('content/B1U1MxHJl.json').success(function(data) {
        htmls[file.name] = file.read_text()

    for file in Path("content").glob("*.json"):
        data = json.loads(file.read_text())
        data["mediaId"] = ytids[normalize(data["title"])]
        file.write_text(json.dumps(data))
        for html_file, html_content in htmls.items():
            if str(file) in html_content:
                if "htmlfile" in data:
                    raise ValueError("Two HTML files points to the same JSON??")
                data["htmlfile"] = html_file
        from_website[normalize(data["title"])] = data

    for file in Path(PYVIDEO_CLONE / "pycon-fr-2016" / "videos").glob("*.json"):
        data = json.loads(file.read_text())
        data["path"] = file.resolve()
        from_pyvideo[normalize(data["title"])] = data

    merge(ytids, from_website, from_pyvideo, from_dl_afpy_org)


main()
