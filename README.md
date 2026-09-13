# Find duplicates

A Click-based CLI for interacting with the Emy API of a Docker-based Emy installation.

## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```

## Emy memory sizing

> **Important:** For capacity planning, allow approximately **0.75 MiB of Emy RAM per fingerprinted track**, plus headroom for filesystem cache, the OS, and other services.

This is an empirical scaling observation, not a guaranteed Emy implementation detail. In a measured dataset of 11,814 tracks, persistent audio signatures were stored under `sfdata/` as one `trackRef_*.bin` file per track. The directory occupied 3.673 GiB on disk, averaging 326 KiB of serialized signature data per track. Emy's steady-state anonymous RAM was approximately 8.6 GiB: about 2.34 times the serialized `sfdata` size, or 763 KiB per track.

Observed scaling is approximately 0.73 GiB of RAM per 1,000 tracks (7.28 GiB per 10,000 tracks). During startup, Emy used high CPU while anonymous RAM increased, then settled at a stable memory plateau with near-zero CPU. This strongly suggests that Emy deserializes and/or transforms the signatures into a larger, search-optimized in-memory representation. The much smaller Lucene indexes, `query_matches` and `tracks_search` (approximately 24 MiB combined), do not account for the memory consumption.

Linear scaling is a planning assumption only; it has been measured at the approximately 11,800-track point, not validated across multiple dataset sizes.

## Installation

The project-local launcher will bootstrap `.venv` for you on first run:

```bash
./find-duplicates --help
```

It expects a local `python3.10+` to be available and will stop with a clear error if the machine only has an older Python.

If you prefer the explicit workflow, create a virtual environment, install the project, and then run the CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
find-duplicates --help
```

## Usage

The CLI exposes two commands in the Python Click port:

- `fingerprint`: generate fingerprints for audio files
- `query`: run similarity queries and emit CSV results

Example help output:

```bash
find-duplicates --help
find-duplicates fingerprint --help
find-duplicates query --help
```

The fingerprint command scans a directory recursively for MP3 files, reads metadata with `exiftool`, and uploads files to Emy concurrently. The upload payload includes ExifTool-derived filename and directory metadata so matching tracks can be traced back later:

```bash
find-duplicates fingerprint /path/to/mp3s
find-duplicates fingerprint /path/to/mp3s --jobs 16
```

Global options:

```bash
find-duplicates --base-url http://localhost:3340/api/v1.1 fingerprint /path/to/mp3s
EMY_AUTHORIZATION="Basic QWRtaW46" find-duplicates fingerprint /path/to/mp3s
```

## Query

The Python `query` command scans a directory recursively for MP3 files, reads metadata with `exiftool`, submits files to Emy's query endpoint concurrently, and prints CSV results to stdout in input order.

```bash
find-duplicates query /path/to/mp3s
find-duplicates query /path/to/mp3s --confidence .75
find-duplicates query /path/to/mp3s --coverage .75 -E exclude.yaml
find-duplicates query /path/to/mp3s --jobs 16
```

CSV columns:

```text
filename,directory,title,album,artist,success,confidence,coverage,info
```

Each returned match is emitted as its own CSV row. When a query returns multiple matches, the submitted file columns are repeated for each match row.

When neither `--confidence` nor `--coverage` is specified, the CLI defaults to `minConfidence=.90` to match the legacy behavior. The exclude file accepts YAML keys such as `artists` and `albums`; values are treated as case-insensitive literal prefixes.

## Query Reference

A working `curl` command:

```
curl --request POST \
--url 'http://localhost:3340/api/v1.1/Query?minConfidence=0.2&minCoverage=0&registerMatches=true' \
--header 'authorization: Basic QWRtaW46' \
--header 'accept: application/json' \
--header 'content-type: multipart/form-data' \
-F file=@file-name.mp3 | jq .
```

## Errors

Connection failures and API validation errors are reported to stderr. Query results continue to be emitted as CSV so failures remain visible in downstream processing.

## TODO

- Error handling

## References

- [Audio Fingerprinting API](https://emysound.com/blog/open-source/2021/06/05/audio-fingerprinting-api.html)
- [JSON API](https://emysound.readme.io/reference/json-api)
