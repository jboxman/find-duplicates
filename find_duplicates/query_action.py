from __future__ import annotations

import csv
import json
import mimetypes
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, NamedTuple

import click
import requests
import yaml

from .emy import (
    CliError,
    build_track_payload,
    clone_session,
    iter_audio_files,
    parse_error_payload,
)

QUERY_CSV_HEADER = [
    "filename",
    "directory",
    "title",
    "album",
    "artist",
    "success",
    "confidence",
    "coverage",
    "album",
    "path",
    "fileSize",
    "info",
]


def run(
    session: requests.Session,
    directory: Path,
    *,
    confidence: float | None,
    coverage: float | None,
    exclude_from: Path | None,
    max_workers: int,
) -> None:
    paths = iter_audio_files(directory)
    if not paths:
        return

    excludes = load_exclude_file(exclude_from) if exclude_from else {}
    exclude_artists = compile_exclude_patterns(excludes.get("artists"))
    exclude_albums = compile_exclude_patterns(excludes.get("albums"))
    exclude_paths = compile_exclude_paths(excludes.get("paths"))
    paths = [path for path in paths if not matches_excluded_path(exclude_paths, path)]

    query_params = build_query_params(confidence=confidence, coverage=coverage)
    writer = csv.writer(click.get_text_stream("stdout"))
    writer.writerow(QUERY_CSV_HEADER)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(
            lambda path: query_path(
                session,
                path,
                query_params=query_params,
                exclude_artists=exclude_artists,
                exclude_albums=exclude_albums,
            ),
            paths,
        ):
            if result is None:
                continue
            for message, is_err in result.messages:
                click.echo(message, err=is_err)
            for row in result.rows:
                writer.writerow(row)


class QueryResult(NamedTuple):
    rows: list[list[str]]
    messages: list[tuple[str, bool]]


def query_path(
    session: requests.Session,
    path: Path,
    *,
    query_params: dict[str, str],
    exclude_artists: list[re.Pattern[str]],
    exclude_albums: list[re.Pattern[str]],
) -> QueryResult | None:
    worker_session = clone_session(session)
    error = ""
    results: list[dict[str, Any]] = []
    metadata_fields: dict[str, str] = {}
    messages: list[tuple[str, bool]] = []

    try:
        payload, metadata_fields = build_track_payload(path)

        if matches_any(exclude_artists, metadata_fields.get("artistName", "")):
            return None
        if matches_any(exclude_albums, metadata_fields.get("albumName", "")):
            return None

        results = post_query(
            worker_session,
            path,
            payload,
            query_params,
        )
    except requests.RequestException as exc:
        messages.extend(
            [
                (f"Failed to upload: {path}", True),
                (str(exc), True),
            ]
        )

        response = exc.response
        error_payload = None
        if response is not None:
            error_payload = parse_error_payload(response)
            if error_payload is not None:
                messages.append((json.dumps(error_payload, indent=2), True))
            elif response.text.strip():
                messages.append((response.text.strip(), True))

        error = format_error(error_payload) or str(exc)
        if is_empty_file_error(error_payload):
            messages.append(
                (
                    f"Large files are rejected by Emy. File size: {path.stat().st_size} bytes.",
                    True,
                )
            )
    except CliError as exc:
        messages.extend(
            [
                (f"Failed to upload: {path}", True),
                (str(exc), True),
            ]
        )
        error = str(exc)

    return QueryResult(
        rows=build_rows(path, metadata_fields, results, error),
        messages=messages,
    )


def post_query(
    session: requests.Session,
    path: Path,
    payload: dict[str, str],
    query_params: dict[str, str],
) -> list[dict[str, Any]]:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with path.open("rb") as file_handle:
        response = session.post(
            f"{session.base_url}/query",
            params=query_params,
            data=payload,
            files={"file": (path.name, file_handle, mime_type)},
            timeout=120,
        )

    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise CliError(f"Query returned invalid JSON for {path}.") from exc

    if not isinstance(payload, list):
        raise CliError(f"Query returned an unexpected payload for {path}.")

    return payload


def build_query_params(
    *, confidence: float | None, coverage: float | None
) -> dict[str, str]:
    params: dict[str, str] = {}
    has_threshold = False

    if confidence is not None:
        params["minConfidence"] = format_decimal(confidence)
        has_threshold = True
    if coverage is not None:
        params["minCoverage"] = format_decimal(coverage)
        has_threshold = True
    if not has_threshold:
        params["minConfidence"] = ".90"

    return params


def build_rows(
    path: Path,
    metadata_fields: dict[str, str],
    results: list[dict[str, Any]],
    error: str,
) -> list[list[str]]:
    source_columns = [
        path.name,
        str(path.parent),
        metadata_fields.get("songTitle", ""),
        metadata_fields.get("albumName", ""),
        metadata_fields.get("artistName", ""),
    ]

    if not results:
        row = list(source_columns)
        row.append("Error" if error else "No")
        row.extend(["", "", "", "", "", error])
        return [row]

    rows: list[list[str]] = []
    for item in results:
        row = list(source_columns)
        audio = item.get("audio") if isinstance(item, dict) else None
        coverage = audio.get("coverage") if isinstance(audio, dict) else None

        row.append("Yes")
        row.append(stringify_value(get_nested(coverage, "queryCoverage")))
        row.append(stringify_value(get_nested(coverage, "trackCoverage")))
        row.extend(format_match_columns(item))
        row.append(format_match_info(item))
        rows.append(row)

    return rows


def format_match_columns(item: dict[str, Any]) -> list[str]:
    return [
        extract_match_album(item),
        extract_match_path(item),
        extract_match_file_size(item),
    ]


def format_match_info(item: Any) -> str:
    if not isinstance(item, dict):
        return ""

    track = item.get("track")
    if not isinstance(track, dict):
        return ""

    title = stringify_value(track.get("title"))
    artist = stringify_value(track.get("artist"))
    if not title and not artist:
        return ""
    return f"{title}:{artist}"


def extract_match_album(item: Any) -> str:
    meta_fields = get_track_meta_fields(item)
    return stringify_value(meta_fields.get("album"))


def extract_match_file_size(item: Any) -> str:
    meta_fields = get_track_meta_fields(item)
    return stringify_value(meta_fields.get("fileSize"))


def extract_match_path(item: Any) -> str:
    meta_fields = get_track_meta_fields(item)
    filename = stringify_value(meta_fields.get("filename"))
    directory = stringify_value(meta_fields.get("directory"))

    if filename and directory:
        return str(Path(directory) / filename)
    return directory or filename


def get_track_meta_fields(item: Any) -> dict[str, Any]:
    track = item.get("track") if isinstance(item, dict) else None
    meta_fields = track.get("metaFields") if isinstance(track, dict) else None
    return meta_fields if isinstance(meta_fields, dict) else {}


def get_nested(mapping: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(mapping, dict):
        return ""
    return mapping.get(key, "")


def stringify_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def load_exclude_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise CliError(f"Cannot open configuration file: {path}") from exc
    except yaml.YAMLError as exc:
        raise CliError("Cannot parse configuration file. The YAML is invalid.") from exc

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise CliError("Exclude configuration must be a YAML mapping.")
    return payload


def compile_exclude_patterns(values: Any) -> list[re.Pattern[str]]:
    if not isinstance(values, list):
        return []

    patterns: list[re.Pattern[str]] = []
    for value in values:
        if isinstance(value, (str, int, float)):
            patterns.append(re.compile(rf"^{re.escape(str(value))}", re.IGNORECASE))
    return patterns


def matches_any(patterns: list[re.Pattern[str]], value: str) -> bool:
    return any(pattern.search(value) for pattern in patterns)


def compile_exclude_paths(values: Any) -> list[Path]:
    if not isinstance(values, list):
        return []

    paths: list[Path] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        path = Path(value)
        paths.append(path.resolve() if path.is_absolute() else path)
    return paths


def matches_excluded_path(exclusions: list[Path], path: Path) -> bool:
    candidate = path.resolve()
    for exclusion in exclusions:
        if exclusion.is_absolute():
            if candidate == exclusion:
                return True
        elif candidate.parts[-len(exclusion.parts) :] == exclusion.parts:
            return True
    return False


def format_error(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""

    code = payload.get("code")
    message = payload.get("message")
    if code is None or not isinstance(message, str):
        return ""
    return f"{code}:{message}"


def is_empty_file_error(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False

    message = payload.get("message")
    return isinstance(message, str) and "empty file" in message.lower()


def format_decimal(value: float) -> str:
    text = f"{value:g}"
    return text if not text.startswith("0.") else text[1:]
