from __future__ import annotations

from pathlib import Path

import click
import requests

from .emy import CliError, DEFAULT_AUTHORIZATION, DEFAULT_BASE_URL, build_session
from .fingerprint_action import run as run_fingerprint_action


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
    ctx.obj = build_session(base_url=base_url, authorization=authorization)


@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.pass_obj
def fingerprint(session: requests.Session, directory: Path) -> None:
    """Generate fingerprints for audio files."""
    run_fingerprint_action(session, directory)


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def query(directory: str) -> None:
    """Perform a similarity query for audio files."""
    raise CliError("`query` has not been ported yet. Start with `fingerprint`.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
