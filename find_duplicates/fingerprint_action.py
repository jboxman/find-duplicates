from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import click
import requests

from .emy import (
    CliError,
    clone_session,
    iter_audio_files,
    parse_error_payload,
    post_track,
)

class FingerprintResult(NamedTuple):
    messages: list[tuple[str, bool]]


def run(session: requests.Session, directory: Path, *, max_workers: int) -> None:
    paths = iter_audio_files(directory)
    if not paths:
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(lambda path: fingerprint_path(session, path), paths):
            for message, is_err in result.messages:
                click.echo(message, err=is_err)


def fingerprint_path(session: requests.Session, path: Path) -> FingerprintResult:
    worker_session = clone_session(session)

    try:
        response = post_track(worker_session, path)
        response.raise_for_status()
        return FingerprintResult(messages=[(f"Uploaded: {path}", True)])
    except CliError as exc:
        return FingerprintResult(
            messages=[
                (f"Failed to upload: {path}", True),
                (str(exc), True),
            ],
        )
    except requests.RequestException as exc:
        messages: list[tuple[str, bool]] = [
            (f"Failed to upload: {path}", True),
            (str(exc), True),
        ]

        response = exc.response
        error_payload = None
        if response is not None:
            error_payload = parse_error_payload(response)
            if error_payload is not None:
                messages.append((json.dumps(error_payload, indent=2), True))
            elif response.text.strip():
                messages.append((response.text.strip(), True))

        message = ""
        if isinstance(error_payload, dict):
            raw_message = error_payload.get("message")
            if isinstance(raw_message, str):
                message = raw_message

        if "empty file" in message.lower():
            size = path.stat().st_size
            messages.append(
                (f"Large files are rejected by Emy. File size: {size} bytes.", True)
            )

        return FingerprintResult(messages=messages)
