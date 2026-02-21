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

from core.command_parser import CommandParser, EntityExtractor, IntentClassifier


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


# ---------------------------------------------------------------------------
# 4. Unit: EntityExtractor – spaCy dependency parsing + regex fallback
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spacy_available():
    """Return True iff spaCy *and* en_core_web_sm are available."""
    try:
        import spacy  # noqa: F401
        spacy.load("en_core_web_sm")
        return True
    except (ImportError, OSError):
        return False


@pytest.fixture(scope="module")
def real_extractor(spacy_available):
    """EntityExtractor with spaCy loaded (or auto-skipped if unavailable)."""
    if not spacy_available:
        pytest.skip("spaCy / en_core_web_sm not installed")
    ext = EntityExtractor()
    ext._load()  # force-load so tests don't pay cold-start cost
    return ext


class TestEntityExtractor:
    """
    Covers the four failing cases identified in the audit plus regression
    tests for the classic regex patterns.

    Tests that require spaCy are auto-skipped when en_core_web_sm is missing.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _regex_only_extractor():
        """Return an EntityExtractor whose spaCy layer is forcibly disabled."""
        ext = EntityExtractor()
        ext._available = False  # skip load attempt
        ext._nlp = None
        return ext

    # ------------------------------------------------------------------
    # Audit failure cases – require spaCy
    # ------------------------------------------------------------------

    def test_no_folder_word(self, real_extractor):
        """'to the Archive' – no word 'folder' – should still extract 'archive'."""
        result = real_extractor.extract_destination(
            "move pdfs to the archive",
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None, "Expected a destination but got None"
        assert "archive" in result.lower(), (
            f"Expected 'archive' in result, got: {result!r}"
        )

    def test_into_preposition(self, real_extractor):
        """'into Backup' – preposition 'into' instead of 'to'."""
        result = real_extractor.extract_destination(
            "move files into backup",
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None, "Expected a destination but got None"
        assert "backup" in result.lower(), (
            f"Expected 'backup' in result, got: {result!r}"
        )

    def test_absolute_path_windows(self, real_extractor):
        """Absolute Windows path – always detected regardless of spaCy."""
        text = "move files to c:/users/rolan/documents/work"
        result = real_extractor.extract_destination(
            text,
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None, "Expected an absolute path destination but got None"
        assert "rolan" in result.lower() or "documents" in result.lower(), (
            f"Expected the path in result, got: {result!r}"
        )

    def test_stopword_destination(self, real_extractor):
        """'to my documents' – leading stopword 'my' must be stripped."""
        result = real_extractor.extract_destination(
            "move photos to my documents",
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None, "Expected a destination but got None"
        # After stripping 'my', 'documents' should survive
        assert "documents" in result.lower(), (
            f"Expected 'documents' in result, got: {result!r}"
        )

    # ------------------------------------------------------------------
    # Absolute-path detection is always active (no spaCy needed)
    # ------------------------------------------------------------------

    def test_absolute_path_no_spacy(self):
        """Absolute path is detected even when spaCy is disabled."""
        ext = self._regex_only_extractor()
        result = ext.extract_destination(
            "move files to c:/users/rolan/documents/work",
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None
        assert "rolan" in result.lower() or "documents" in result.lower()

    # ------------------------------------------------------------------
    # Regex fallback – spaCy disabled
    # ------------------------------------------------------------------

    def test_regex_fallback_classic_pattern(self):
        """When spaCy is disabled the regex fallback must still work."""
        ext = self._regex_only_extractor()
        parser = CommandParser()
        result = ext.extract_destination(
            "move pdfs to archive folder",
            regex_fallback_fn=parser._extract_destination_regex,
        )
        assert result is not None, "Regex fallback should find 'archive'"
        assert "archive" in result.lower(), f"Got: {result!r}"

    def test_regex_fallback_end_of_string(self):
        """Regex end-of-string pattern: 'move photos to backup'."""
        ext = self._regex_only_extractor()
        parser = CommandParser()
        result = ext.extract_destination(
            "move photos to backup",
            regex_fallback_fn=parser._extract_destination_regex,
        )
        assert result is not None
        assert "backup" in result.lower()

    # ------------------------------------------------------------------
    # Source extraction
    # ------------------------------------------------------------------

    def test_source_from_preposition(self, real_extractor):
        """'from downloads' – source folder extraction via 'from' preposition."""
        result = real_extractor.extract_source(
            "find files from downloads",
            regex_fallback_fn=lambda t: None,
        )
        assert result is not None, "Expected a source but got None"
        assert "downloads" in result.lower(), f"Got: {result!r}"

    def test_source_regex_fallback(self):
        """Source regex fallback: 'organize downloads folder'."""
        ext = self._regex_only_extractor()
        parser = CommandParser()
        result = ext.extract_source(
            "organize downloads folder",
            regex_fallback_fn=parser._extract_source_regex,
        )
        assert result is not None
        assert "downloads" in result.lower()

    # ------------------------------------------------------------------
    # Thread-safety
    # ------------------------------------------------------------------

    def test_thread_safety(self, real_extractor):
        """Concurrent calls to extract_destination must not raise."""
        import threading
        errors = []

        def _call():
            try:
                real_extractor.extract_destination(
                    "move files to archive",
                    regex_fallback_fn=lambda t: None,
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent calls raised: {errors}"

    # ------------------------------------------------------------------
    # CommandParser integration – full pipeline with EntityExtractor
    # ------------------------------------------------------------------

    def test_parse_command_no_folder_word(self, spacy_available):
        """CommandParser.parse_command handles 'to the Archive' end-to-end.

        The intent classifier may return 'move' or 'copy' depending on model
        state – both are valid relocate-style actions.  What we care about
        here is that EntityExtractor correctly surfaces 'archive' as the
        destination even though the word 'folder' is absent.
        """
        if not spacy_available:
            pytest.skip("spaCy / en_core_web_sm not installed")
        parser = CommandParser()
        result = parser.parse_command("move all pdfs to the archive")
        assert result.get("action") in ("move", "copy"), (
            f"Expected 'move' or 'copy', got {result.get('action')!r}. "
            f"Full result: {result}"
        )
        dest = result.get("destination", "")
        assert dest and "archive" in dest.lower(), (
            f"Expected 'archive' in destination, got: {dest!r}"
        )

    def test_parse_command_into_prep(self, spacy_available):
        """CommandParser.parse_command handles 'into Backup'.

        Accepts move or copy – the entity extraction of 'backup' is what
        we're validating, not the intent classification.
        """
        if not spacy_available:
            pytest.skip("spaCy / en_core_web_sm not installed")
        parser = CommandParser()
        result = parser.parse_command("move images into backup")
        assert result.get("action") in ("move", "copy"), (
            f"Expected 'move' or 'copy', got {result.get('action')!r}"
        )
        dest = result.get("destination", "")
        assert dest and "backup" in dest.lower(), f"Got: {dest!r}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

