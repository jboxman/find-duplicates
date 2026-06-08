from pathlib import Path
import unittest

from find_duplicates.query_action import QUERY_CSV_HEADER, build_rows


class QueryActionTests(unittest.TestCase):
    def test_build_rows_includes_metadata_columns(self) -> None:
        rows = build_rows(
            Path("/tmp/query/input.mp3"),
            {
                "songTitle": "Input Song",
                "albumName": "Input Album",
                "artistName": "Input Artist",
            },
            [
                {
                    "track": {
                        "title": "I know boy",
                        "artist": "Yulbox",
                        "metaFields": {
                            "filename": "01-I know boy-Yulbox-192kbit-360s.mp3",
                            "directory": "/Volumes/public/all-mp3s",
                            "fileSize": "8.7 MB",
                            "album": "I know boy",
                        },
                    },
                    "audio": {
                        "coverage": {
                            "queryCoverage": 0.9988,
                            "trackCoverage": 0.9989,
                        }
                    },
                }
            ],
            "",
        )

        self.assertEqual(
            rows,
            [[
                "input.mp3",
                "/tmp/query",
                "Input Song",
                "Input Album",
                "Input Artist",
                "Yes",
                "0.9988",
                "0.9989",
                "I know boy",
                "/Volumes/public/all-mp3s/01-I know boy-Yulbox-192kbit-360s.mp3",
                "8.7 MB",
                "I know boy:Yulbox",
            ]],
        )

    def test_build_rows_returns_one_row_per_match(self) -> None:
        rows = build_rows(
            Path("/tmp/query/input.mp3"),
            {
                "songTitle": "Input Song",
                "albumName": "Input Album",
                "artistName": "Input Artist",
            },
            [
                {
                    "track": {
                        "title": "Track One",
                        "artist": "Artist One",
                        "metaFields": {
                            "filename": "track-one.mp3",
                            "directory": "/matches/one",
                            "fileSize": "1 MB",
                            "album": "Album One",
                        },
                    },
                    "audio": {
                        "coverage": {
                            "queryCoverage": 0.91,
                            "trackCoverage": 0.92,
                        }
                    },
                },
                {
                    "track": {
                        "title": "Track Two",
                        "artist": "Artist Two",
                        "metaFields": {
                            "filename": "track-two.mp3",
                            "directory": "/matches/two",
                            "fileSize": "2 MB",
                            "album": "Album Two",
                        },
                    },
                    "audio": {
                        "coverage": {
                            "queryCoverage": 0.81,
                            "trackCoverage": 0.82,
                        }
                    },
                },
            ],
            "",
        )

        self.assertEqual(
            rows,
            [
                [
                    "input.mp3",
                    "/tmp/query",
                    "Input Song",
                    "Input Album",
                    "Input Artist",
                    "Yes",
                    "0.91",
                    "0.92",
                    "Album One",
                    "/matches/one/track-one.mp3",
                    "1 MB",
                    "Track One:Artist One",
                ],
                [
                    "input.mp3",
                    "/tmp/query",
                    "Input Song",
                    "Input Album",
                    "Input Artist",
                    "Yes",
                    "0.81",
                    "0.82",
                    "Album Two",
                    "/matches/two/track-two.mp3",
                    "2 MB",
                    "Track Two:Artist Two",
                ],
            ],
        )

    def test_build_rows_leaves_metadata_columns_empty_when_no_results(self) -> None:
        rows = build_rows(Path("/tmp/query/input.mp3"), {}, [], "")

        self.assertEqual(
            rows,
            [[
                "input.mp3",
                "/tmp/query",
                "",
                "",
                "",
                "No",
                "",
                "",
                "",
                "",
                "",
                "",
            ]],
        )

    def test_header_includes_metadata_columns(self) -> None:
        self.assertEqual(
            QUERY_CSV_HEADER,
            [
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
            ],
        )


if __name__ == "__main__":
    unittest.main()
