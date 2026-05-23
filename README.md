# Find duplicates

A Click-based CLI for interacting with the Emy API of a Docker-based Emy installation.

## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```

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

The fingerprint command scans a directory recursively for MP3 files, reads metadata with `exiftool`, and uploads each file to Emy. The upload payload includes ExifTool-derived filename and directory metadata so matching tracks can be traced back later:

```bash
find-duplicates fingerprint /path/to/mp3s
```

Global options:

```bash
find-duplicates --base-url http://localhost:3340/api/v1.1 fingerprint /path/to/mp3s
EMY_AUTHORIZATION="Basic QWRtaW46" find-duplicates fingerprint /path/to/mp3s
```

## Query

The Python `query` command scans a directory recursively for MP3 files, reads metadata with `exiftool`, submits each file to Emy's query endpoint, and prints CSV results to stdout.

```bash
find-duplicates query /path/to/mp3s
find-duplicates query /path/to/mp3s --confidence .75
find-duplicates query /path/to/mp3s --coverage .75 -E exclude.yaml
```

CSV columns:

```text
filename,directory,title,album,artist,success,confidence,coverage,info
```

When neither `--confidence` nor `--coverage` is specified, the CLI defaults to `minConfidence=.90` to match the legacy behavior. The exclude file accepts YAML keys such as `artists` and `albums`; values are treated as case-insensitive literal prefixes.

## Legacy Notes

The original Node/Commander implementation remains in `lib/` during the migration so the existing behavior can be ported incrementally.

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

Errors from where the ssh tunnel went away:

```
filename,title,album,artist,success,confidence,coverage,matches
Failed to upload: /path/to/file.mp3
write EPIPE
TypeError: Cannot read properties of undefined (reading 'data')
    at Command.action (...lib/query-action.js:70:41)
    at processTicksAndRejections (node:internal/process/task_queues:96:5)
    at async Command.parseAsync (...node_modules/commander/lib/command.js:935:5)
    at async main (...find-duplicates:24:5)
```

```
filename,title,album,artist,success,confidence,coverage,matches
Failed to upload: /path/to/file.mp3
connect ECONNREFUSED 127.0.0.1:3340
TypeError: Cannot read properties of undefined (reading 'data')
    at Command.action (...lib/query-action.js:70:41)
    at processTicksAndRejections (node:internal/process/task_queues:96:5)
    at async Command.parseAsync (...node_modules/commander/lib/command.js:935:5)
    at async main (...find-duplicates:24:5)
```

## TODO

- Tests
- Error handling

## References

- [Audio Fingerprinting API](https://emysound.com/blog/open-source/2021/06/05/audio-fingerprinting-api.html)
- [JSON API](https://emysound.readme.io/reference/json-api)
