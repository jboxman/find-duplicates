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


def _iter_audio_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES
    )


def _run_exiftool(path: Path) -> dict[str, Any]:
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


def _pick_tag(metadata: dict[str, Any], *keys: str) -> str:
    for key in reversed(keys):
        raw = metadata.get(key)
        if isinstance(raw, (str, int, float)):
            value = str(raw).strip()
            if value:
                return value
    return ""


def _build_track_payload(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    metadata = _run_exiftool(path)

    album = _pick_tag(
        metadata,
        "ID3v1:Album",
        "Lyrics3:ExtendedAlbumName",
        "ID3v2_3:Album",
        "ID3v2_4:Album",
    )
    title = _pick_tag(
        metadata,
        "ID3v1:Title",
        "Lyrics3:ExtendedTrackTitle",
        "ID3v2_3:Title",
        "ID3v2_4:Title",
    )
    artist = _pick_tag(
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
    if album:
        payload["metaFields[album]"] = album
    if title:
        payload["title"] = title
    if artist:
        payload["artist"] = artist

    return payload, fields


def _build_session(base_url: str, authorization: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"authorization": authorization})
    session.base_url = base_url.rstrip("/")
    return session


def _post_track(session: requests.Session, path: Path) -> None:
    payload, _ = _build_track_payload(path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with path.open("rb") as file_handle:
        response = session.post(
            f"{session.base_url}/tracks",
            data=payload,
            files={"file": (path.name, file_handle, mime_type)},
            timeout=120,
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        error_message = _format_emy_error(response)
        raise CliError(f"Failed to upload {path}: {error_message}") from exc


def _format_emy_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("message")
        if code and message:
            return f"{code}: {message}"
        if message:
            return str(message)

    text = response.text.strip()
    if text:
        return text

    return f"HTTP {response.status_code}"


@click.group()
@click.option(
    "--base-url",
    default=DEFAULT_BASE_URL,
    show_default=True,
    help="Base URL for the Emy API.",
)
@click.option(
    "--authorization",
    default=DEFAULT_AUTHORIZATION,
    show_default=False,
    envvar="EMY_AUTHORIZATION",
    help="Authorization header value for the Emy API.",
)
@click.pass_context
def cli(ctx: click.Context, base_url: str, authorization: str) -> None:
    """Interact with the Emy audio fingerprinting API."""
    ctx.obj = _build_session(base_url=base_url, authorization=authorization)


@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.pass_obj
def fingerprint(session: requests.Session, directory: Path) -> None:
    """Generate fingerprints for audio files."""
    paths = _iter_audio_files(directory)
    if not paths:
        click.echo("No MP3 files found.", err=True)
        return

    failures = 0

    for path in paths:
        try:
            _post_track(session, path)
            click.echo(f"Uploaded: {path}", err=True)
        except CliError as exc:
            failures += 1
            click.echo(str(exc), err=True)

            # Emy reports oversized files as "empty file".
            if "empty file" in str(exc).lower():
                size = path.stat().st_size
                click.echo(
                    f"Large files are rejected by Emy. File size: {size} bytes.",
                    err=True,
                )

    if failures:
        raise SystemExit(1)


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def query(directory: str) -> None:
    """Perform a similarity query for audio files."""
    raise CliError("`query` has not been ported yet. Start with `fingerprint`.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
