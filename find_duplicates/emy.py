from __future__ import annotations

import json
import mimetypes
import subprocess
import uuid
from pathlib import Path
from typing import Any

import click
import requests

DEFAULT_BASE_URL = "http://localhost:3340/api/v1.1"
DEFAULT_AUTHORIZATION = "Basic QWRtaW46"
SUPPORTED_AUDIO_SUFFIXES = {".mp3"}


class CliError(click.ClickException):
    """Project-specific CLI exception."""


def build_session(base_url: str, authorization: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"authorization": authorization})
    session.base_url = base_url.rstrip("/")
    return session


def iter_audio_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES
    )


def run_exiftool(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "exiftool",
                "-j",
                "-s",
                "-filename",
                "-directory",
                "-filesize#",
                "-audiobitrate#",
                "-title",
                "-album",
                "-artist",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CliError("`exiftool` is required but was not found in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "unknown error"
        raise CliError(f"Failed to read metadata for {path}: {stderr}") from exc

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CliError(f"Exiftool returned invalid JSON for {path}.") from exc

    if not payload or not isinstance(payload[0], dict):
        raise CliError(f"Exiftool returned no metadata for {path}.")

    return payload[0]

def stringify_metadata_value(raw: Any) -> str:
    if not isinstance(raw, (str, int, float)):
        return ""
    return str(raw).strip()


def build_track_payload(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    metadata = run_exiftool(path)

    album = stringify_metadata_value(metadata.get("Album"))
    title = stringify_metadata_value(metadata.get("Title"))
    artist = stringify_metadata_value(metadata.get("Artist"))
    bitrate = stringify_metadata_value(metadata.get("AudioBitrate"))

    fields = {
        "albumName": album,
        "songTitle": title,
        "artistName": artist,
    }

    payload = {
        "id": str(uuid.uuid4()),
        "mediaType": "Audio",
    }

    filename = stringify_metadata_value(metadata.get("FileName"))
    if filename:
        payload["metaFields[filename]"] = filename
    directory = stringify_metadata_value(metadata.get("Directory"))
    if directory:
        payload["metaFields[directory]"] = directory
    file_size = stringify_metadata_value(metadata.get("FileSize"))
    if file_size:
        payload["metaFields[fileSize]"] = file_size
    if bitrate:
        payload["metaFields[audioBitrate]"] = bitrate
    if album:
        payload["metaFields[album]"] = album
    if title:
        payload["title"] = title
    if artist:
        payload["artist"] = artist

    return payload, fields


def post_track(session: requests.Session, path: Path) -> requests.Response:
    payload, _ = build_track_payload(path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with path.open("rb") as file_handle:
        return session.post(
            f"{session.base_url}/tracks",
            data=payload,
            files={"file": (path.name, file_handle, mime_type)},
            timeout=120,
        )


def parse_error_payload(response: requests.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None
