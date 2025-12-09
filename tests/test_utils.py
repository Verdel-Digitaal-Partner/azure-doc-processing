import unittest

from azure_doc_processing.utils import (find_latest_version_file,
                                        get_latest_version)


class TestGetLatestVersion(unittest.TestCase):
    """Unit tests for get_latest_version."""

    def test_happy_paths(self):
        """Typical, valid inputs should return the highest version."""
        cases = [
            (["0.1.0", "0.1.1", "0.2.0"], "0.2.0"),  # simple ascending
            (["1.2.3", "1.10.0", "2.0.0", "1.9.9"], "2.0.0"),  # unsorted, larger major wins
            (["3.4.5", "3.4.5", "3.4.4"], "3.4.5"),  # duplicates present
            (["01.0.0", "1.0.0"], "1.0.0"),  # leading zero in major
            (["10.0.0", "9.9.9"], "10.0.0"),  # two-digit major
            (["0.0.9", "0.0.10"], "0.0.10"),  # patch rollover
        ]
        for versions, expected in cases:
            with self.subTest(versions=versions):
                self.assertEqual(get_latest_version(versions), expected)

    def test_malformed_component_raises_value_error(self):
        """Non-numeric parts should bubble up as ValueError from int()."""
        with self.assertRaises(ValueError):
            get_latest_version(["1.0.alpha"])

    def test_empty_list_raises_index_error(self):
        """The implementation indexes [-1]; an empty list should raise."""
        with self.assertRaises(IndexError):
            get_latest_version([])


class TestFindLatestVersionFile(unittest.TestCase):
    """Unit tests for find_latest_version_file."""

    def test_basic_selection(self):
        paths = [
            "prompts/messages/v1.0.0/prompt.json",
            "prompts/messages/v1.2.3/prompt.json",
            "prompts/messages/v0.9.9/prompt.json",
        ]
        expected = "prompts/messages/v1.2.3/prompt.json"
        self.assertEqual(find_latest_version_file(paths), expected)

    def test_duplicate_version_last_file_wins(self):
        """If a version appears multiple times, the last mapping wins (dict overwrite)."""
        paths = [
            "prompts/v2.0.0/first.json",
            "prompts/v2.0.0/second.json",  # should be returned
        ]
        expected = "prompts/v2.0.0/second.json"
        self.assertEqual(find_latest_version_file(paths), expected)

    def test_no_valid_versions_raises_value_error(self):
        with self.assertRaises(ValueError):
            find_latest_version_file(["prompts/no_version/prompt.json"])

    def test_ignores_paths_without_versions(self):
        paths = [
            "prompts/messages/readme.txt",  # no version
            "prompts/messages/v0.0.1/prompt.json",
        ]
        expected = "prompts/messages/v0.0.1/prompt.json"
        self.assertEqual(find_latest_version_file(paths), expected)


if __name__ == "__main__":
    unittest.main()
