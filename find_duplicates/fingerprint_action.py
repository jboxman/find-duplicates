from __future__ import annotations

import json
from pathlib import Path

import click
import requests

from .emy import CliError, iter_audio_files, parse_error_payload, post_track


def run(session: requests.Session, directory: Path) -> None:
    paths = iter_audio_files(directory)
    if not paths:
        return

    for path in paths:
        try:
            response = post_track(session, path)
            response.raise_for_status()
            click.echo(f"Uploaded: {path}", err=True)
        except CliError as exc:
            click.echo(f"Failed to upload: {path}", err=True)
            click.echo(str(exc), err=True)
        except requests.RequestException as exc:
            click.echo(f"Failed to upload: {path}", err=True)
            click.echo(str(exc), err=True)

            response = exc.response
            error_payload = None
            if response is not None:
                error_payload = parse_error_payload(response)
                if error_payload is not None:
                    click.echo(json.dumps(error_payload, indent=2), err=True)
                elif response.text.strip():
                    click.echo(response.text.strip(), err=True)

            message = ""
            if isinstance(error_payload, dict):
                raw_message = error_payload.get("message")
                if isinstance(raw_message, str):
                    message = raw_message

            if "empty file" in message.lower():
                size = path.stat().st_size
                click.echo(
                    f"Large files are rejected by Emy. File size: {size} bytes."
                )
