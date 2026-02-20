"""
Tests for the Hybrid NLP Intent Classifier in CommandParser
============================================================

Two test groups:

1. ``TestIntentClassifier`` – unit-tests for ``IntentClassifier.detect_intent()``
   directly, testing colloquial phrasings that the old regex loop misses.
   Skipped automatically when sentence-transformers is not installed.

2. ``TestCommandParserRegexFallback`` – integration tests for
   ``CommandParser.parse_command()`` with the ST classifier *mocked out*,
   verifying that the regex keyword loop still produces correct results when
   sentence-transformers is unavailable.

3. ``TestCommandParserEndToEnd`` – end-to-end integration tests that call
   ``parse_command()`` with the real IntentClassifier (if available) using
   the natural-language phrasings listed in the audit.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Make `core` importable from the tests directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.command_parser import CommandParser, IntentClassifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def st_available():
    """Return True iff sentence-transformers can be imported."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture(scope="module")
def real_classifier(st_available):
    """Real IntentClassifier, loads the ST model once per test session."""
    if not st_available:
        pytest.skip("sentence-transformers not installed")
    clf = IntentClassifier()
    # Force-load so the model is ready
    clf._load()
    return clf


@pytest.fixture
def parser_no_st():
    """CommandParser with IntentClassifier forcibly disabled (simulates no ST)."""
    parser = CommandParser()
    # Patch the classifier so it always says 'unknown' (forces regex fallback)
    mock_clf = MagicMock(spec=IntentClassifier)
    mock_clf.detect_intent.return_value = 'unknown'
    mock_clf.is_available = False
    parser._intent_clf = mock_clf
    return parser


# ---------------------------------------------------------------------------
# 1. Unit: IntentClassifier.detect_intent() – requires ST
# ---------------------------------------------------------------------------

class TestIntentClassifier:
    """These tests only run when sentence-transformers is installed."""

    MOVE_PHRASES = [
        "take my PDFs and put them in Archive",
        "shift photos to backup",
        "transfer all images into the old folder",
        "send my documents to the archive folder",
    ]

    COPY_PHRASES = [
        "duplicate all spreadsheets to Backup",
        "make a copy of reports in the archive",
    ]

    ORGANIZE_PHRASES = [
        "archive my old documents",
        "clean up the downloads directory",
        "tidy up my files",
        "categorize everything in my desktop folder",
    ]

    FIND_PHRASES = [
        "locate files modified last week",
        "show me all the PDFs",
        "look for images from yesterday",
    ]

    DELETE_PHRASES = [
        "get rid of temp files older than 30 days",
        "purge old log files",
        "erase all executables",
    ]

    RENAME_PHRASES = [
        "relabel all screenshots with the date",
        "add a date prefix to all photos",
    ]

    UNKNOWN_PHRASES = [
        "xyzzy frobble worp",
        "the quick brown fox",
    ]

    @pytest.mark.parametrize("phrase", MOVE_PHRASES)
    def test_move_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'move', (
            f"Expected 'move' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", COPY_PHRASES)
    def test_copy_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'copy', (
            f"Expected 'copy' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", ORGANIZE_PHRASES)
    def test_organize_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'organize', (
            f"Expected 'organize' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", FIND_PHRASES)
    def test_find_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'find', (
            f"Expected 'find' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", DELETE_PHRASES)
    def test_delete_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'delete', (
            f"Expected 'delete' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", RENAME_PHRASES)
    def test_rename_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'rename', (
            f"Expected 'rename' for: {phrase!r}"
        )

    @pytest.mark.parametrize("phrase", UNKNOWN_PHRASES)
    def test_unknown_intent(self, real_classifier, phrase):
        assert real_classifier.detect_intent(phrase) == 'unknown', (
            f"Expected 'unknown' for: {phrase!r}"
        )

    def test_is_available_true(self, real_classifier):
        """After loading the model is_available must be True."""
        assert real_classifier.is_available is True

    def test_thread_safety(self, real_classifier):
        """detect_intent should not raise under concurrent calls."""
        import threading
        errors = []

        def _call():
            try:
                real_classifier.detect_intent("move files to backup")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent calls raised: {errors}"


# ---------------------------------------------------------------------------
# 2. Integration: CommandParser regex fallback (no ST)
# ---------------------------------------------------------------------------

class TestCommandParserRegexFallback:
    """Verify the regex keyword loop still works when ST is unavailable."""

    def test_move_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("move all PDFs to Archive folder")
        assert result['action'] == 'move'

    def test_copy_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("copy all images to Backup folder")
        assert result['action'] == 'copy'

    def test_find_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("find all documents modified last week")
        assert result['action'] == 'find'

    def test_delete_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("delete temp files older than 7 days")
        assert result['action'] == 'delete'

    def test_rename_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("rename all screenshots include date")
        assert result['action'] == 'rename'

    def test_organize_keyword(self, parser_no_st):
        result = parser_no_st.parse_command("organize my Downloads folder")
        assert result['action'] == 'organize'

    def test_unknown_returns_helpful_message(self, parser_no_st):
        result = parser_no_st.parse_command("xyzzy frobble worp")
        assert result['action'] == 'unknown'
        assert 'error' in result
        # The error message must name the supported operations
        assert 'move' in result['error']
        assert 'find' in result['error']


# ---------------------------------------------------------------------------
# 3. End-to-end: CommandParser with real ST (the audit's failing cases)
# ---------------------------------------------------------------------------

class TestCommandParserEndToEnd:
    """Run parse_command() with the real ST classifier on the failing phrasings."""

    @pytest.fixture(scope="class", autouse=True)
    def require_st(self, st_available):
        if not st_available:
            pytest.skip("sentence-transformers not installed")

    def test_take_pdfs_and_put_in_archive(self):
        parser = CommandParser()
        result = parser.parse_command("take my PDFs and put them in Archive")
        assert result['action'] == 'move', (
            f"Expected 'move', got {result['action']!r}. Full result: {result}"
        )

    def test_shift_photos_to_backup(self):
        parser = CommandParser()
        result = parser.parse_command("shift photos to backup")
        assert result['action'] == 'move', (
            f"Expected 'move', got {result['action']!r}."
        )

    def test_archive_old_documents(self):
        parser = CommandParser()
        result = parser.parse_command("archive my old documents")
        assert result['action'] in ('organize', 'move'), (
            f"Expected 'organize' or 'move', got {result['action']!r}."
        )

    def test_locate_files(self):
        parser = CommandParser()
        result = parser.parse_command("locate files modified last week")
        assert result['action'] == 'find', (
            f"Expected 'find', got {result['action']!r}."
        )

    def test_get_rid_of_temp_files(self):
        parser = CommandParser()
        result = parser.parse_command(
            "get rid of temp files older than 30 days"
        )
        assert result['action'] == 'delete', (
            f"Expected 'delete', got {result['action']!r}."
        )

    def test_relabel_screenshots(self):
        parser = CommandParser()
        result = parser.parse_command("relabel all screenshots with date")
        assert result['action'] == 'rename', (
            f"Expected 'rename', got {result['action']!r}."
        )

    def test_nonsense_is_unknown(self):
        parser = CommandParser()
        result = parser.parse_command("xyzzy frobble worp")
        assert result['action'] == 'unknown'

    def test_unknown_error_message_is_helpful(self):
        """The 'unknown' error message must contain actionable guidance."""
        parser = CommandParser()
        result = parser.parse_command("totally unrecognised input zzz")
        assert result['action'] == 'unknown'
        msg = result.get('error', '')
        assert 'move' in msg, "Error message should list supported intents"
        assert 'organize' in msg
        assert 'find' in msg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
