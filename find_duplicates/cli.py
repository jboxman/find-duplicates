from __future__ import annotations

from pathlib import Path

import click
import requests

from .emy import (
    DEFAULT_AUTHORIZATION,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_WORKERS,
    build_session,
)
from .fingerprint_action import run as run_fingerprint_action
from .query_action import run as run_query_action


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
@click.option(
    "-j",
    "--jobs",
    default=DEFAULT_MAX_WORKERS,
    show_default=True,
    type=click.IntRange(1),
    help="Number of files to process concurrently.",
)
@click.pass_obj
def fingerprint(session: requests.Session, directory: Path, jobs: int) -> None:
    """Generate fingerprints for audio files."""
    run_fingerprint_action(session, directory, max_workers=jobs)


@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--confidence",
    type=click.FloatRange(0, 1),
    help="Specifies a confidence %, such as .75",
)
@click.option(
    "--coverage",
    type=click.FloatRange(0, 1),
    help="Specifies a coverage %, such as .75",
)
@click.option(
    "-E",
    "--exclude-from",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Specifies an ignore list in YAML format",
)
@click.option(
    "-j",
    "--jobs",
    default=DEFAULT_MAX_WORKERS,
    show_default=True,
    type=click.IntRange(1),
    help="Number of files to process concurrently.",
)
@click.pass_obj
def query(
    session: requests.Session,
    directory: Path,
    confidence: float | None,
    coverage: float | None,
    exclude_from: Path | None,
    jobs: int,
) -> None:
    """Perform a similarity query for audio files."""
    run_query_action(
        session,
        directory,
        confidence=confidence,
        coverage=coverage,
        exclude_from=exclude_from,
        max_workers=jobs,
    )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
