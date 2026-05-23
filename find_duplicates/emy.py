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
            ["exiftool", "-j", "-G1", str(path)],
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


def pick_tag(metadata: dict[str, Any], *keys: str) -> str:
    for key in reversed(keys):
        raw = metadata.get(key)
        if isinstance(raw, (str, int, float)):
            value = str(raw).strip()
            if value:
                return value
    return ""


def build_track_payload(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    metadata = run_exiftool(path)

    album = pick_tag(
        metadata,
        "ID3v1:Album",
        "Lyrics3:ExtendedAlbumName",
        "ID3v2_3:Album",
        "ID3v2_4:Album",
    )
    title = pick_tag(
        metadata,
        "ID3v1:Title",
        "Lyrics3:ExtendedTrackTitle",
        "ID3v2_3:Title",
        "ID3v2_4:Title",
    )
    artist = pick_tag(
        metadata,
        "ID3v1:Artist",
        "Lyrics3:ExtendedArtistName",
        "ID3v2_3:Artist",
        "ID3v2_4:Artist",
    )

    fields = {
        "albumName": album,
        "songTitle": title,
        "artistName": artist,
    }

    payload = {
        "id": str(uuid.uuid4()),
        "mediaType": "Audio",
    }

    filename = metadata.get("System:FileName")
    if isinstance(filename, str) and filename.strip():
        payload["metaFields[filename]"] = filename.strip()
    directory = metadata.get("System:Directory")
    if isinstance(directory, str) and directory.strip():
        payload["metaFields[directory]"] = directory.strip()
    file_size = metadata.get("System:FileSize")
    if isinstance(file_size, (str, int, float)):
        value = str(file_size).strip()
        if value:
            payload["metaFields[fileSize]"] = value
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
