# Find duplicates

A CLI for interacting with the Emy API of a Docker-based Emy installation. Supports a subset of the tracks and query APIs.

## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```

## Installation

Clone the repo, run `npm i`, and then run the CLI from the root of the repository, or use `npm link` to install.

## Usage

Supports uploading a directory of MP3 files to either fingerprint or query against existing fingerprints for similarity matching.

Query output is in the form of a CSV for easy importing into a spreadsheet, such as Google Sheets:

```
filename,title,album,artist,success,confidence,coverage,info
```

Help output:

```
./find-duplicates
Usage: find-duplicates [options] [command]

Options:
  -h, --help             display help for command

Commands:
  fingerprint <dir>      Generate fingerprints for audio files
  query [options] <dir>  Perform a similarity query for audio files
  help [command]         display help for command


 ./find-duplicates fingerpint --help
Usage: find-duplicates [options] [command]

Options:
  -h, --help             display help for command

Commands:
  fingerprint <dir>      Generate fingerprints for audio files
  query [options] <dir>  Perform a similarity query for audio files
  help [command]         display help for command

./find-duplicates query --help
Usage: find-duplicates query [options] <dir>

Perform a similarity query for audio files

Arguments:
  dir                        Directory to scan recursively for audio files

Options:
  --confidence <decimal>     Specifies a confidence %, such as .75
  --coverage <decimal>       Specifies a coverage %, such as .75
  -E, --exclude-from <file>  Specifies an ignore list in YAML format
  -h, --help                 display help for command
```

## Query

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
