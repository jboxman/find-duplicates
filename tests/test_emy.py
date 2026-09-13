from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from find_duplicates.emy import DEFAULT_MAX_WORKERS, build_track_payload, run_exiftool


class EmyTests(unittest.TestCase):
    def test_default_max_workers_limits_server_load(self) -> None:
        self.assertEqual(DEFAULT_MAX_WORKERS, 4)

    @patch("find_duplicates.emy.subprocess.run")
    def test_run_exiftool_requests_specific_json_fields(self, run_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='[{"FileName":"file.mp3","Directory":"/tmp","FileSize":123,"AudioBitrate":192000,"Title":"Song","Album":"Album","Artist":"Artist"}]',
            stderr="",
        )

        metadata = run_exiftool(Path("/tmp/file.mp3"))

        self.assertEqual(
            run_mock.call_args.args[0],
            [
                "exiftool",
                "-j",
                "-s",
                "-filename",
                "-directory",
                "-filesize#",
                "-audiobitrate#",
                "-title",
                "-album",
                "-artist",
                "/tmp/file.mp3",
            ],
        )
        self.assertEqual(
            metadata,
            {
                "FileName": "file.mp3",
                "Directory": "/tmp",
                "FileSize": 123,
                "AudioBitrate": 192000,
                "Title": "Song",
                "Album": "Album",
                "Artist": "Artist",
            },
        )

    @patch("find_duplicates.emy.run_exiftool")
    def test_build_track_payload_maps_specific_fields(self, run_exiftool_mock) -> None:
        run_exiftool_mock.return_value = {
            "FileName": " file.mp3 ",
            "Directory": " /tmp ",
            "FileSize": 123,
            "AudioBitrate": 192000,
            "Title": " Song ",
            "Album": " Album ",
            "Artist": " Artist ",
        }

        payload, fields = build_track_payload(Path("/tmp/file.mp3"))

        self.assertEqual(
            fields,
            {
                "albumName": "Album",
                "songTitle": "Song",
                "artistName": "Artist",
            },
        )
        self.assertEqual(payload["mediaType"], "Audio")
        self.assertEqual(payload["metaFields[filename]"], "file.mp3")
        self.assertEqual(payload["metaFields[directory]"], "/tmp")
        self.assertEqual(payload["metaFields[fileSize]"], "123")
        self.assertEqual(payload["metaFields[audioBitrate]"], "192000")
        self.assertEqual(payload["metaFields[album]"], "Album")
        self.assertEqual(payload["title"], "Song")
        self.assertEqual(payload["artist"], "Artist")


if __name__ == "__main__":
    unittest.main()
