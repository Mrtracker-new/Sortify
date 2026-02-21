import logging
import re
import threading
from pathlib import Path
import datetime

# ---------------------------------------------------------------------------
# Semantic intent classifier (sentence-transformers, optional dependency)
# ---------------------------------------------------------------------------

class IntentClassifier:
    """Semantic intent router using sentence-transformers prototype embeddings.

    Falls back gracefully to 'unknown' when sentence-transformers is not
    installed or the model cannot be loaded, allowing CommandParser to use the
    original regex keyword loop as a backup.
    """

    INTENT_PROTOTYPES = {
        'move':     [
            'move files to folder',
            'move all documents to archive folder',
            'transfer files to directory',
            'put files into archive folder',
            'put documents in backup folder',
            'shift files to folder',
            'send files to destination folder',
            'take files and put them in folder',
            'relocate files to directory',
            'move photos to backup',
        ],
        'copy':     [
            'copy files to folder',
            'copy documents to backup folder',
            'duplicate files to another folder',
            'make a copy of documents in folder',
            'make a copy of reports in archive',
            'create a copy and place in archive',
            'make a backup copy in directory',
        ],
        'organize': [
            'organize folder by type',
            'sort files in directory',
            'clean up directory',
            'tidy up folder',
            'arrange files in directory',
            'categorize files in folder',
            'structure files in directory',
            'tidy and sort old documents',
            'clean and sort archived documents',
        ],
        'find':     [
            'find files in folder',
            'search for files matching criteria',
            'locate files in directory',
            'locate documents modified recently',
            'show me all files',
            'show me all images in folder',
            'list files matching criteria',
            'which files are in folder',
            'look for files in directory',
            'look for images from yesterday',
            'where are my files',
        ],
        'delete':   [
            'delete files from folder',
            'remove files from directory',
            'get rid of old files',
            'clean old files older than days',
            'erase files from folder',
            'wipe files from directory',
            'purge old files from folder',
            'trash files older than days',
        ],
        'rename':   [
            'rename files in folder',
            'change filename of files',
            'add date to filename',
            'rename all files in directory',
            'relabel files with date',
            'add prefix to filename',
            'change name of all files',
            'label files with date',
        ],
    }

    # Cosine-similarity threshold: scores below this map to 'unknown'.
    # 0.45 gives good recall on short/colloquial phrasings while still
    # rejecting clearly unrelated input.
    THRESHOLD = 0.45

    def __init__(self):
        self._model = None
        self._proto_embeddings = None
        self._st_util = None
        self._lock = threading.Lock()
        self._available = None  # None = not yet tried

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> bool:
        """Lazy-load sentence-transformers and pre-compute prototype embeddings.

        Idempotent – safe to call multiple times; the model is loaded only once.
        Returns True if the classifier is ready, False otherwise.
        """
        if self._available is not None:
            return self._available

        try:
            from sentence_transformers import SentenceTransformer, util as st_util

            self._st_util = st_util
            self._model = SentenceTransformer('all-MiniLM-L6-v2')

            # Pre-compute prototype embeddings (done once, cached forever)
            self._proto_embeddings = {
                intent: self._model.encode(phrases, convert_to_tensor=True)
                for intent, phrases in self.INTENT_PROTOTYPES.items()
            }

            self._available = True
            logging.info("IntentClassifier: sentence-transformers loaded successfully")

        except ImportError:
            self._available = False
            logging.info(
                "IntentClassifier: sentence-transformers not installed – "
                "CommandParser will use regex keyword fallback"
            )
        except Exception as e:  # model download failure, etc.
            self._available = False
            logging.warning(f"IntentClassifier: failed to load model – {e}")

        return self._available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_intent(self, text: str) -> str:
        """Return the best-matching intent name or ``'unknown'``.

        Args:
            text: Raw (already lower-cased) command string.

        Returns:
            One of ``'move'``, ``'copy'``, ``'organize'``, ``'find'``,
            ``'delete'``, ``'rename'``, or ``'unknown'``.
        """
        with self._lock:
            if not self._load():
                return 'unknown'  # Caller falls back to regex loop

            query_emb = self._model.encode(text, convert_to_tensor=True)

            best_intent, best_score = 'unknown', 0.0
            for intent, proto_embs in self._proto_embeddings.items():
                score = float(self._st_util.cos_sim(query_emb, proto_embs).max())
                if score > best_score:
                    best_score, best_intent = score, intent

            result = best_intent if best_score >= self.THRESHOLD else 'unknown'
            logging.debug(
                f"IntentClassifier: '{text}' → '{result}' (score={best_score:.3f})"
            )
            return result

    @property
    def is_available(self) -> bool:
        """True if the sentence-transformers model is loaded and ready."""
        return bool(self._available)


# ---------------------------------------------------------------------------
# Synonym normalisation helpers
# ---------------------------------------------------------------------------

# Maps colloquial verbs → canonical intent keyword.
# Used by _extract_destination / _extract_source to widen pattern matching.
_VERB_SYNONYMS = {
    'shift':      'move',
    'transfer':   'move',
    'relocate':   'move',
    'put':        'move',
    'take':       'move',
    'send':       'move',
    'duplicate':  'copy',
    'backup':     'copy',
    'tidy':       'organize',
    'clean':      'organize',
    'arrange':    'organize',
    'categorize': 'organize',
    'archive':    'organize',
    'locate':     'find',
    'look':       'find',
    'search':     'find',
    'show':       'find',
    'erase':      'delete',
    'remove':     'delete',
    'purge':      'delete',
    'wipe':       'delete',
    'trash':      'delete',
    'relabel':    'rename',
}

# Also maps colloquial destination prepositions
_DESTINATION_PREPS = ['to', 'into', 'in', 'inside', 'at']
_SOURCE_PREPS = ['from', 'in', 'inside', 'within']

# Noise words that should never be treated as a folder name on their own
_NOISE_WORDS = frozenset({'the', 'a', 'an', 'my', 'your', 'our', 'this', 'that'})


def _normalise_command(text: str) -> str:
    """Replace synonym verbs in *text* with their canonical equivalents."""
    words = text.split()
    return ' '.join(_VERB_SYNONYMS.get(w, w) for w in words)


# ---------------------------------------------------------------------------
# Entity extractor – spaCy primary, regex fallback
# ---------------------------------------------------------------------------

class EntityExtractor:
    """Extract destination and source folder names from natural-language commands.

    **Primary strategy** – spaCy dependency parsing:
    Walks the parsed token tree looking for prepositional-object (``pobj``)
    tokens whose governing preposition is one of the known destination or
    source prepositions.  Also considers named entities (``GPE``, ``ORG``,
    ``PRODUCT``, ``FAC``) that appear after a relevant preposition.

    **Absolute-path detection** (always active):
    A regex is applied first to catch paths such as
    ``C:/Users/alice/Documents/Work`` or ``/home/alice/files`` regardless
    of spaCy availability.

    **Regex fallback** – if spaCy (or ``en_core_web_sm``) is unavailable,
    the original keyword-based patterns are used automatically.

    Lazy-loaded and thread-safe (mirrors :class:`IntentClassifier`).
    """

    # Entity types that are credible folder/path candidates when NER is used
    _USABLE_ENT_TYPES = frozenset({'GPE', 'ORG', 'PRODUCT', 'FAC', 'LOC', 'WORK_OF_ART'})

    # Pre-compiled regex for absolute path detection (Windows & POSIX)
    _ABS_PATH_RE = re.compile(
        r'(?:[A-Za-z]:[/\\]|/)[\w/\\. -]+',
        re.IGNORECASE
    )

    def __init__(self):
        self._nlp = None
        self._lock = threading.Lock()
        self._available = None  # None = not yet tried

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> bool:
        """Lazy-load ``en_core_web_sm``.  Idempotent, thread-safe.

        Returns ``True`` if spaCy is ready, ``False`` otherwise.
        """
        if self._available is not None:
            return self._available

        try:
            import spacy  # noqa: PLC0415
            self._nlp = spacy.load('en_core_web_sm')
            self._available = True
            logging.info("EntityExtractor: spaCy en_core_web_sm loaded successfully")
        except ImportError:
            self._available = False
            logging.info(
                "EntityExtractor: spaCy not installed – using regex fallback"
            )
        except OSError:
            self._available = False
            logging.warning(
                "EntityExtractor: en_core_web_sm model not found – "
                "run `python -m spacy download en_core_web_sm`. "
                "Falling back to regex."
            )
        except Exception as e:
            self._available = False
            logging.warning(f"EntityExtractor: spaCy load failed – {e}")

        return self._available

    # ------------------------------------------------------------------
    # Span helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _noun_chunk_for_token(doc, token):
        """Return the full noun-chunk text that contains *token*, or its text."""
        for chunk in doc.noun_chunks:
            if token.i >= chunk.start and token.i < chunk.end:
                return chunk.text.strip()
        return token.text.strip()

    @staticmethod
    def _clean(candidate: str) -> str | None:
        """Strip leading noise words; return None if nothing useful remains."""
        words = candidate.split()
        while words and words[0].lower() in _NOISE_WORDS:
            words = words[1:]
        result = ' '.join(words).strip()
        return result if result and result.lower() not in _NOISE_WORDS else None

    # ------------------------------------------------------------------
    # Extraction helpers shared by destination and source
    # ------------------------------------------------------------------

    def _spacy_pobj_extract(self, text: str, preps: list[str]) -> str | None:
        """Use spaCy dependency parse to find pobj after any of *preps*.

        Returns the best candidate string or ``None``.
        """
        with self._lock:
            ready = self._load()

        if not ready:
            return None

        doc = self._nlp(text)

        # Pass 1 – dependency tree: pobj tokens whose head is a target prep
        for token in doc:
            if token.dep_ == 'pobj' and token.head.text.lower() in preps:
                candidate = self._noun_chunk_for_token(doc, token)
                cleaned = self._clean(candidate)
                if cleaned:
                    logging.debug(
                        f"EntityExtractor: dep-parse found '{cleaned}' "
                        f"(prep='{token.head.text}')"
                    )
                    return cleaned.lower()

        # Pass 2 – NER: named entities appearing after a target preposition
        for ent in doc.ents:
            if ent.label_ not in self._USABLE_ENT_TYPES:
                continue
            # Check whether a target preposition appears just before this entity
            if ent.start > 0:
                prev_token = doc[ent.start - 1]
                if prev_token.text.lower() in preps or (
                    prev_token.text.lower() == 'the'
                    and ent.start > 1
                    and doc[ent.start - 2].text.lower() in preps
                ):
                    cleaned = self._clean(ent.text)
                    if cleaned:
                        logging.debug(
                            f"EntityExtractor: NER found '{cleaned}' "
                            f"(label={ent.label_})"
                        )
                        return cleaned.lower()

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_destination(
        self,
        text: str,
        regex_fallback_fn,
    ) -> str | None:
        """Extract the destination folder from *text*.

        Args:
            text: Lower-cased command string.
            regex_fallback_fn: Callable that accepts *text* and returns
                ``str | None``.  Called when spaCy is unavailable or
                returns nothing useful.

        Returns:
            Folder name / path string, or ``None``.
        """
        # Always-active: absolute / relative path detection
        abs_match = self._ABS_PATH_RE.search(text)
        if abs_match:
            logging.debug(
                f"EntityExtractor: abs-path found '{abs_match.group()}'"
            )
            return abs_match.group().strip()

        # spaCy dependency + NER pass
        spacy_result = self._spacy_pobj_extract(text, _DESTINATION_PREPS)
        if spacy_result:
            return spacy_result

        # Regex fallback
        return regex_fallback_fn(text)

    def extract_source(
        self,
        text: str,
        regex_fallback_fn,
    ) -> str | None:
        """Extract the source folder from *text*.

        Args:
            text: Lower-cased command string.
            regex_fallback_fn: Callable that accepts *text* and returns
                ``str | None``.

        Returns:
            Folder name / path string, or ``None``.
        """
        # spaCy dependency + NER pass (no abs-path check for source)
        spacy_result = self._spacy_pobj_extract(text, _SOURCE_PREPS)
        if spacy_result:
            return spacy_result

        # Regex fallback
        return regex_fallback_fn(text)

    @property
    def is_available(self) -> bool:
        """True if spaCy has been loaded successfully."""
        return bool(self._available)



# ---------------------------------------------------------------------------
# Main CommandParser class
# ---------------------------------------------------------------------------

class CommandParser:
    """Parse natural language commands for file operations.

    Intent detection is performed in two stages:

    1. **Semantic stage** (preferred): ``IntentClassifier`` computes cosine
       similarity between the user's command and a set of prototype phrases
       for each intent using ``sentence-transformers/all-MiniLM-L6-v2``.
    2. **Regex fallback**: if sentence-transformers is unavailable (not
       installed, model not downloaded, or running in a minimal frozen bundle)
       the original keyword-in-text loop is used instead.

    Both stages produce a ``parsed_command`` dict that is consumed identically
    by the rest of the application.
    """

    def __init__(self):
        """Initialise the command parser."""
        # Map canonical intent → parse handler
        self.commands = {
            'move':     self._parse_move_command,
            'copy':     self._parse_copy_command,
            'organize': self._parse_organize_command,
            'sort':     self._parse_sort_command,
            'find':     self._parse_find_command,
            'search':   self._parse_find_command,  # regex-fallback alias
            'delete':   self._parse_delete_command,
            'rename':   self._parse_rename_command,
        }

        self.time_patterns = {
            'today':                        self._get_today,
            'yesterday':                    self._get_yesterday,
            'last week':                    self._get_last_week,
            'last month':                   self._get_last_month,
            r'older than (\d+) days':       self._get_older_than_days,
        }

        # Semantic intent classifier (lazy-loaded on first parse_command call)
        self._intent_clf = IntentClassifier()

        # spaCy-powered entity extractor (lazy-loaded, falls back to regex)
        self._entity_extractor = EntityExtractor()

        # Thread-local storage: holds the *original* (pre-normalised) command
        # text so that _extract_destination / _extract_source always see the
        # user's words, not the synonym-substituted form.
        self._tls = threading.local()

        logging.info("CommandParser initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_command(self, command_text: str) -> dict:
        """Parse a natural language command.

        Args:
            command_text: Raw user input string.

        Returns:
            dict with at minimum ``{'action': <str>}``.  An ``'error'`` key
            is present when the action is ``'unknown'`` or a required
            parameter is missing.
        """
        command_text = command_text.lower().strip()

        # ── Stage 1: semantic intent detection ─────────────────────────
        intent = self._intent_clf.detect_intent(command_text)

        if intent != 'unknown' and intent in self.commands:
            logging.info(f"CommandParser: ST intent='{intent}' for '{command_text}'")
            # Store original text so entity extractors see the user's actual
            # words (e.g. 'archive', 'backup'), not the synonym-normalised
            # equivalents ('organize', 'copy').
            self._tls.original_text = command_text
            # Normalise synonyms before keyword checks in parse handlers.
            normalised = _normalise_command(command_text)
            return self.commands[intent](normalised)

        # ── Stage 2: regex keyword fallback ────────────────────────────
        # Also triggered when sentence-transformers is unavailable.
        for cmd_type, parser in self.commands.items():
            if cmd_type in command_text:
                logging.info(
                    f"CommandParser: regex fallback matched '{cmd_type}' "
                    f"for '{command_text}'"
                )
                return parser(command_text)

        # ── Nothing matched ─────────────────────────────────────────────
        supported = ', '.join(
            f"'{k}'" for k in ('move', 'copy', 'organize', 'find', 'delete', 'rename')
        )
        hint = (
            "Could not understand command. Supported operations: "
            f"{supported}. "
            "Try phrasing like: \"move all PDFs to Archive folder\", "
            "\"find images modified last week\", or \"organize Downloads folder\"."
        )
        return {'action': 'unknown', 'error': hint}

    # ------------------------------------------------------------------
    # Parse handlers
    # ------------------------------------------------------------------

    def _parse_move_command(self, command_text):
        """Parse a move command.

        Example: ``"Move all PDFs to Archive folder"``
        """
        result = {'action': 'move'}

        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types

        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint

        destination = self._extract_destination(command_text)
        if destination:
            result['destination'] = destination
        else:
            result['error'] = 'No destination folder specified'

        return result

    def _parse_copy_command(self, command_text):
        """Parse a copy command.

        Example: ``"Copy all images to Backup folder"``
        """
        result = self._parse_move_command(command_text)
        result['action'] = 'copy'
        return result

    def _parse_organize_command(self, command_text):
        """Parse an organize command.

        Example: ``"Organize Downloads folder"``
        """
        result = {'action': 'organize'}

        source = self._extract_source(command_text)
        if source:
            result['source'] = source

        if 'by type' in command_text:
            result['method'] = 'type'
        elif 'by date' in command_text:
            result['method'] = 'date'
        elif 'by size' in command_text:
            result['method'] = 'size'
        else:
            result['method'] = 'type'  # default

        return result

    def _parse_sort_command(self, command_text):
        """Parse a sort command (alias for organize)."""
        result = self._parse_organize_command(command_text)
        result['action'] = 'sort'
        return result

    def _parse_find_command(self, command_text):
        """Parse a find/search command.

        Example: ``"Find all documents modified last week"``
        """
        result = {'action': 'find'}

        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types

        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint

        source = self._extract_source(command_text)
        if source:
            result['source'] = source

        return result

    def _parse_delete_command(self, command_text):
        """Parse a delete command.

        Example: ``"Delete temporary files older than 30 days"``
        """
        result = {'action': 'delete'}

        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types
        else:
            result['error'] = 'No file types specified for deletion'
            return result

        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint
        else:
            result['error'] = 'Time constraint required for deletion commands'

        return result

    def _parse_rename_command(self, command_text):
        """Parse a rename command.

        Example: ``"Rename all screenshots to include date"``
        """
        result = {'action': 'rename'}

        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types

        if 'include date' in command_text or 'add date' in command_text:
            result['pattern'] = 'date'
        elif 'sequential' in command_text:
            result['pattern'] = 'sequential'
        elif 'lowercase' in command_text:
            result['pattern'] = 'lowercase'
        elif 'uppercase' in command_text:
            result['pattern'] = 'uppercase'
        else:
            result['error'] = 'No rename pattern specified'

        return result

    # ------------------------------------------------------------------
    # Parameter extractors
    # ------------------------------------------------------------------

    def _extract_file_types(self, command_text):
        """Extract file types from command text."""
        file_types = []

        type_keywords = {
            'pdfs':        '.pdf',
            'pdf':         '.pdf',
            'documents':   ['doc', 'docx', 'pdf', 'txt'],
            'document':    ['doc', 'docx', 'pdf', 'txt'],
            'images':      ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'image':       ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'photos':      ['jpg', 'jpeg', 'png'],
            'photo':       ['jpg', 'jpeg', 'png'],
            'videos':      ['mp4', 'avi', 'mov', 'mkv'],
            'video':       ['mp4', 'avi', 'mov', 'mkv'],
            'music':       ['mp3', 'wav', 'flac', 'ogg'],
            'audio':       ['mp3', 'wav', 'flac', 'ogg'],
            'archives':    ['zip', 'rar', '7z', 'tar', 'gz'],
            'archive':     ['zip', 'rar', '7z', 'tar', 'gz'],
            'executables': ['exe', 'msi', 'app'],
            'executable':  ['exe', 'msi', 'app'],
            'spreadsheets':['xlsx', 'xls', 'csv'],
            'spreadsheet': ['xlsx', 'xls', 'csv'],
            'scripts':     ['py', 'js', 'sh', 'bat', 'ps1'],
            'script':      ['py', 'js', 'sh', 'bat', 'ps1'],
        }

        for keyword, extensions in type_keywords.items():
            if keyword in command_text:
                if isinstance(extensions, list):
                    file_types.extend(extensions)
                else:
                    file_types.append(extensions)

        # Explicit extensions like ".pdf", ".docx"
        ext_matches = re.findall(r'\.([a-zA-Z0-9]+)', command_text)
        if ext_matches:
            file_types.extend(ext_matches)

        return list(set(file_types)) if file_types else None

    def _extract_time_constraint(self, command_text):
        """Extract time constraints from command text."""
        for pattern, time_func in self.time_patterns.items():
            match = re.search(pattern, command_text)
            if match:
                if len(match.groups()) > 0:
                    return time_func(int(match.group(1)))
                else:
                    return time_func()
        return None

    def _extract_destination(self, command_text):
        """Extract destination folder from command text.

        Uses :class:`EntityExtractor` (spaCy dependency parsing + NER +
        absolute-path regex) as the primary strategy, falling back to
        :meth:`_extract_destination_regex` when spaCy is unavailable.

        .. important::
            Entity extraction is **always** performed on the original
            pre-normalised text (stored in :attr:`_tls.original_text`) so that
            folder names like ``'archive'`` or ``'backup'``  are not silently
            rewritten by :func:`_normalise_command` before we look at them.
        """
        # Prefer original text to avoid synonym-normalisation clobbering folder names
        extract_text = getattr(self._tls, 'original_text', None) or command_text
        return self._entity_extractor.extract_destination(
            extract_text,
            regex_fallback_fn=self._extract_destination_regex,
        )

    def _extract_destination_regex(self, command_text) -> str | None:
        """Pure-regex destination extractor (fallback / tested independently)."""
        # "to/into/in/inside/at X folder"
        for prep in _DESTINATION_PREPS:
            match = re.search(
                rf'\b{re.escape(prep)}\s+([\w\s]+?)\s+(?:folder|directory)\b',
                command_text
            )
            if match:
                return match.group(1).strip()

        # "to/into X" at end of string
        for prep in _DESTINATION_PREPS:
            match = re.search(
                rf'\b{re.escape(prep)}\s+([\w\s]+)$',
                command_text
            )
            if match:
                candidate = match.group(1).strip()
                # Strip leading noise words
                words = candidate.split()
                while words and words[0].lower() in _NOISE_WORDS:
                    words = words[1:]
                candidate = ' '.join(words)
                if candidate and candidate.lower() not in _NOISE_WORDS:
                    return candidate

        return None

    def _extract_source(self, command_text):
        """Extract source folder from command text.

        Uses :class:`EntityExtractor` as the primary strategy, falling back
        to :meth:`_extract_source_regex`.

        .. important::
            Entity extraction is performed on the original pre-normalised text
            (from :attr:`_tls.original_text`) for the same reason as
            :meth:`_extract_destination`.
        """
        extract_text = getattr(self._tls, 'original_text', None) or command_text
        return self._entity_extractor.extract_source(
            extract_text,
            regex_fallback_fn=self._extract_source_regex,
        )

    def _extract_source_regex(self, command_text) -> str | None:
        """Pure-regex source extractor (fallback / tested independently)."""
        # "in/from/within/inside X folder"
        for prep in _SOURCE_PREPS:
            match = re.search(
                rf'\b{re.escape(prep)}\s+([\w\s]+?)\s+(?:folder|directory)\b',
                command_text
            )
            if match:
                return match.group(1).strip()

        # "from X folder" – already handled above, but keep legacy patterns
        match = re.search(r'from\s+([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()

        # "X folder" at the start
        match = re.search(r'^([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()

        return None

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def _get_today(self):
        today = datetime.date.today()
        return {'type': 'date', 'operator': '==', 'value': today}

    def _get_yesterday(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        return {'type': 'date', 'operator': '==', 'value': yesterday}

    def _get_last_week(self):
        one_week_ago = datetime.date.today() - datetime.timedelta(days=7)
        return {'type': 'date', 'operator': '>', 'value': one_week_ago}

    def _get_last_month(self):
        one_month_ago = datetime.date.today() - datetime.timedelta(days=30)
        return {'type': 'date', 'operator': '>', 'value': one_month_ago}

    def _get_older_than_days(self, days):
        x_days_ago = datetime.date.today() - datetime.timedelta(days=days)
        return {'type': 'date', 'operator': '<', 'value': x_days_ago}

    # ------------------------------------------------------------------
    # Execution engine (unchanged)
    # ------------------------------------------------------------------

    def execute_command(self, parsed_command, file_ops):
        """Execute a parsed command using the file operations.

        Args:
            parsed_command: The parsed command dictionary.
            file_ops: ``FileOperations`` instance.

        Returns:
            tuple: ``(success: bool, message: str)``
        """
        try:
            action = parsed_command.get('action')

            if action == 'move':
                return self._execute_move_command(parsed_command, file_ops)
            elif action == 'copy':
                return self._execute_copy_command(parsed_command, file_ops)
            elif action in ('organize', 'sort'):
                return self._execute_organize_command(parsed_command, file_ops)
            elif action == 'find':
                return self._execute_find_command(parsed_command, file_ops)
            elif action == 'delete':
                return self._execute_delete_command(parsed_command, file_ops)
            elif action == 'rename':
                return self._execute_rename_command(parsed_command, file_ops)
            else:
                return False, f"Unknown action: {action}"

        except Exception as e:
            logging.error(f"Error executing command: {e}")
            return False, f"Error: {str(e)}"

    def _execute_move_command(self, command, file_ops):
        """Execute a move command."""
        destination = command.get('destination')
        if not destination:
            return False, "No destination specified"

        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        if not files:
            return False, "No matching files found"

        file_ops.start_operations()

        moved_count = 0
        failed_count = 0
        for file in files:
            try:
                result = file_ops.move_file(file, destination, skip_confirmation=True)
                if result:
                    moved_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logging.error(f"Error moving file {file}: {e}")
                failed_count += 1

        file_ops.finalize_operations()

        if moved_count > 0:
            msg = f"Moved {moved_count} file(s) to {destination}"
            if failed_count > 0:
                msg += f" ({failed_count} failed)"
            return True, msg
        else:
            return False, f"Failed to move files. {failed_count} errors occurred."

    def _execute_copy_command(self, command, file_ops):
        """Execute a copy command."""
        destination = command.get('destination')
        if not destination:
            return False, "No destination specified"

        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        if not files:
            return False, "No matching files found"

        file_ops.start_operations()

        copied_count = 0
        failed_count = 0
        for file in files:
            try:
                result = file_ops.copy_file(file, destination)
                if result:
                    copied_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logging.error(f"Error copying file {file}: {e}")
                failed_count += 1

        file_ops.finalize_operations()

        if copied_count > 0:
            msg = f"Copied {copied_count} file(s) to {destination}"
            if failed_count > 0:
                msg += f" ({failed_count} failed)"
            return True, msg
        else:
            return False, f"Failed to copy files. {failed_count} errors occurred."

    def _execute_organize_command(self, command, file_ops):
        """Execute an organize command."""
        source = command.get('source')
        method = command.get('method', 'type')

        if source:
            source_path = Path(file_ops.base_dir) / source
            if not source_path.exists() or not source_path.is_dir():
                return False, f"Source folder '{source}' not found"
        else:
            source_path = Path(file_ops.base_dir)

        files = [f for f in source_path.glob('*') if f.is_file()]
        if not files:
            return False, "No files found in source folder"

        file_ops.start_operations()

        organized_count = 0
        failed_count = 0
        for file in files:
            try:
                if method == 'type':
                    category = file_ops.categorize_file(file)
                elif method == 'date':
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                    category = f"By Date/{mtime.strftime('%Y-%m')}"
                elif method == 'size':
                    size_kb = file.stat().st_size / 1024
                    if size_kb < 100:
                        category = "By Size/Small (< 100KB)"
                    elif size_kb < 1024:
                        category = "By Size/Medium (100KB - 1MB)"
                    elif size_kb < 10240:
                        category = "By Size/Large (1MB - 10MB)"
                    else:
                        category = "By Size/Very Large (> 10MB)"
                else:
                    category = "Unsorted"

                result = file_ops.move_file(file, category, skip_confirmation=True)
                if result:
                    organized_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logging.error(f"Error organizing file {file}: {e}")
                failed_count += 1

        file_ops.finalize_operations()

        source_name = source if source else "base directory"
        if organized_count > 0:
            msg = f"Organized {organized_count} file(s) from {source_name}"
            if failed_count > 0:
                msg += f" ({failed_count} failed)"
            return True, msg
        else:
            return False, f"Failed to organize files. {failed_count} errors occurred."

    def _execute_find_command(self, command, file_ops):
        """Execute a find command."""
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        if not files:
            return False, "No matching files found"

        examples = [f.name for f in files[:5]]
        examples_str = ', '.join(examples)
        if len(files) > 5:
            examples_str += f" and {len(files) - 5} more"

        return True, f"Found {len(files)} files: {examples_str}"

    def _execute_delete_command(self, command, file_ops):
        """Execute a delete command (dry-run for safety)."""
        if not command.get('time_constraint'):
            return False, "Time constraint required for deletion commands"

        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        if not files:
            return False, "No matching files found"

        examples = [f.name for f in files[:5]]
        examples_str = ', '.join(examples)
        if len(files) > 5:
            examples_str += f" and {len(files) - 5} more"

        return True, f"Would delete {len(files)} files: {examples_str}"

    def _execute_rename_command(self, command, file_ops):
        """Execute a rename command."""
        pattern = command.get('pattern')
        if not pattern:
            return False, "No rename pattern specified"

        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        if not files:
            return False, "No matching files found"

        renamed_count = 0
        for file in files:
            try:
                if pattern == 'date':
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                    date_str = mtime.strftime('%Y-%m-%d')
                    new_name = f"{file.stem}_{date_str}{file.suffix}"
                elif pattern == 'sequential':
                    new_name = f"{file.stem}_{renamed_count + 1:03d}{file.suffix}"
                elif pattern == 'lowercase':
                    new_name = file.name.lower()
                elif pattern == 'uppercase':
                    new_name = file.name.upper()
                else:
                    continue

                new_path = file.parent / new_name
                file.rename(new_path)
                renamed_count += 1
            except Exception as e:
                logging.error(f"Error renaming file {file}: {e}")

        return True, f"Renamed {renamed_count} files"

    # ------------------------------------------------------------------
    # File-matching helper
    # ------------------------------------------------------------------

    def _get_files_matching_criteria(self, command, base_dir):
        """Return a list of ``Path`` objects matching the criteria in *command*."""
        base_path = Path(base_dir)
        if not base_path.exists() or not base_path.is_dir():
            logging.error(f"Base directory does not exist: {base_dir}")
            return []

        try:
            all_files = list(base_path.glob('**/*'))
            matching_files = [f for f in all_files if f.is_file()]
        except Exception as e:
            logging.error(f"Error scanning directory {base_dir}: {e}")
            return []

        # ── Filter by file types ────────────────────────────────────────
        file_types = command.get('file_types')
        if file_types:
            matching_files = [
                f for f in matching_files
                if any(f.name.lower().endswith(f'.{ext.lower()}') for ext in file_types)
            ]

        # ── Filter by time constraint ───────────────────────────────────
        time_constraint = command.get('time_constraint')
        if time_constraint:
            operator = time_constraint.get('operator')
            value    = time_constraint.get('value')

            filtered = []
            for file in matching_files:
                try:
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime).date()
                    if operator == '==' and mtime == value:
                        filtered.append(file)
                    elif operator == '>' and mtime > value:
                        filtered.append(file)
                    elif operator == '<' and mtime < value:
                        filtered.append(file)
                except Exception as e:
                    logging.error(f"Error checking file time for {file}: {e}")
            matching_files = filtered

        # ── Filter by source ────────────────────────────────────────────
        source = command.get('source')
        if source:
            source_path = base_path / source
            if source_path.exists():
                matching_files = [
                    f for f in matching_files
                    if source_path in f.parents or f.parent == source_path
                ]
            else:
                logging.warning(f"Source path does not exist: {source_path}")
                return []

        return matching_files