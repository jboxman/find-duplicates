# Find duplicates

A Click-based CLI for interacting with the Emy API of a Docker-based Emy installation. The current Python port includes the `fingerprint` command and a placeholder `query` command while the rest of the functionality is migrated.

## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```

## Installation

Create a virtual environment, install the project, and then run the CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

The CLI exposes the two long-term commands:

- `fingerprint`: implemented in the Python Click port
- `query`: present as a placeholder until it is migrated

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

The original Node implementation still exists in `lib/query-action.js` as migration reference material. The Click `query` command is not implemented yet.

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
