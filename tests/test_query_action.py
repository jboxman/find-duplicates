from pathlib import Path
import re
import unittest
from unittest.mock import patch

from find_duplicates.query_action import (
    QUERY_CSV_HEADER,
    build_rows,
    compile_exclude_paths,
    matches_excluded_path,
    query_path,
)


class QueryActionTests(unittest.TestCase):
    def test_excluded_paths_accept_partial_and_absolute_paths(self) -> None:
        cases = [
            (Path("/music/path/to/filename.mp3"), "path/to/filename.mp3"),
            (Path("/music/path/to/filename.mp3"), "to/filename.mp3"),
            (Path("/compete/path/filename.mp3"), "/compete/path/filename.mp3"),
        ]

        for path, exclusion in cases:
            with self.subTest(exclusion=exclusion):
                self.assertTrue(
                    matches_excluded_path(compile_exclude_paths([exclusion]), path)
                )

    def test_excluded_paths_match_at_component_boundaries(self) -> None:
        exclusions = compile_exclude_paths(["to/filename.mp3"])

        self.assertFalse(
            matches_excluded_path(
                exclusions,
                Path("/music/not-to/filename.mp3"),
            )
        )

    def test_excluded_paths_keep_absolute_matches_exact(self) -> None:
        exclusions = compile_exclude_paths(["/music/path"])

        self.assertTrue(matches_excluded_path(exclusions, Path("/music/path")))
        self.assertFalse(
            matches_excluded_path(exclusions, Path("/other/music/path"))
        )

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

    @patch("find_duplicates.query_action.post_query")
    @patch("find_duplicates.query_action.build_track_payload")
    @patch("find_duplicates.query_action.clone_session")
    def test_query_path_returns_rows_for_success(
        self,
        clone_session_mock,
        build_track_payload_mock,
        post_query_mock,
    ) -> None:
        worker_session = object()
        clone_session_mock.return_value = worker_session
        build_track_payload_mock.return_value = (
            {"title": "Input Song"},
            {
                "songTitle": "Input Song",
                "albumName": "Input Album",
                "artistName": "Input Artist",
            },
        )
        post_query_mock.return_value = [
            {
                "track": {
                    "title": "Match Song",
                    "artist": "Match Artist",
                    "metaFields": {
                        "filename": "match.mp3",
                        "directory": "/matches",
                        "fileSize": "1 MB",
                        "album": "Match Album",
                    },
                },
                "audio": {
                    "coverage": {
                        "queryCoverage": 0.95,
                        "trackCoverage": 0.96,
                    }
                },
            }
        ]

        result = query_path(
            object(),
            Path("/tmp/input.mp3"),
            query_params={"minConfidence": ".90"},
            exclude_artists=[],
            exclude_albums=[],
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.messages, [])
        self.assertEqual(result.rows[0][0], "input.mp3")
        self.assertEqual(result.rows[0][5], "Yes")
        post_query_mock.assert_called_once_with(
            worker_session,
            Path("/tmp/input.mp3"),
            {"title": "Input Song"},
            {"minConfidence": ".90"},
        )

    @patch("find_duplicates.query_action.clone_session")
    @patch("find_duplicates.query_action.build_track_payload")
    def test_query_path_skips_excluded_artist(
        self,
        build_track_payload_mock,
        clone_session_mock,
    ) -> None:
        clone_session_mock.return_value = object()
        build_track_payload_mock.return_value = (
            {},
            {
                "songTitle": "Input Song",
                "albumName": "Input Album",
                "artistName": "Skip Me",
            },
        )

        result = query_path(
            object(),
            Path("/tmp/input.mp3"),
            query_params={"minConfidence": ".90"},
            exclude_artists=[re.compile("^Skip\\ Me", re.IGNORECASE)],
            exclude_albums=[],
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
