import os
from pathlib import Path
import mimetypes
import sys
import importlib.util
import logging

logger = logging.getLogger('Sortify')

# spaCy is loaded lazily in the background thread (ModelLoaderThread) and
# injected via set_nlp_model().  We do NOT import it here at module level:
# on some Windows systems the torch/c10.dll it depends on can only be
# initialised after a main-thread pre-warm, so an eager import here would
# produce a noisy WinError 1114 before the UI even appears.
SPACY_AVAILABLE = False  # updated to True by set_nlp_model() at runtime

# Guard-import the advanced ML classifier.  We import lazily (inside the class)
# to avoid circular-import issues and to keep startup cost near zero.
try:
    from .ai_categorizer import AIFileClassifier as _AIFileClassifier
    _ML_CLASSIFIER_AVAILABLE = True
except Exception as _import_err:  # pragma: no cover
    _ML_CLASSIFIER_AVAILABLE = False
    logger.debug("AIFileClassifier not available for categorization pipeline: %s", _import_err)

class FileCategorizationAI:
    def __init__(self, nlp=None):
        """
        Initialize file categorization.
        
        Args:
            nlp: Optional pre-loaded spaCy model. If None, will attempt to load.
                 If loading fails, will fall back to pattern-based categorization.
        """
        self.nlp = nlp
        self.ai_enabled = (nlp is not None)
        
        # Define categories here so they're always available
        self.categories = {
            'documents': {
                'word': ['.doc', '.docx', '.rtf', '.odt'],
                'excel': ['.xls', '.xlsx', '.csv', '.ods'],
                'powerpoint': ['.ppt', '.pptx', '.odp'],
                'pdf': ['.pdf'],
                'text': ['.txt', '.md', '.log']
            },
            'images': {
                'jpg': ['.jpg', '.jpeg', '.jfif'],
                'png': ['.png'],
                'gif': ['.gif'],
                'bmp': ['.bmp'],
                'webp': ['.webp'],
                'heic': ['.heic', '.heif'],
                'tiff': ['.tiff', '.tif'],
                'vector': ['.svg', '.ai', '.eps'],
                'raw': ['.raw', '.cr2', '.nef', '.arw', '.dng'],
                'whatsapp': [],  # Extensions handled by filename pattern in categorize_file
                'telegram': [],  # Extensions handled by filename pattern in categorize_file
                'instagram': [],  # Extensions handled by filename pattern in categorize_file
                'facebook': [],  # Extensions handled by filename pattern in categorize_file
                'ai': []  # AI-generated images detected by pattern
            },
            'ai_images': {
                'chatgpt': [],  # Extensions handled by filename pattern
                'midjourney': [],  # Extensions handled by filename pattern
                'stable_diffusion': [],  # Extensions handled by filename pattern
                'bing': [],  # Extensions handled by filename pattern
                'bard': [],  # Extensions handled by filename pattern
                'claude': [],  # Extensions handled by filename pattern
                'other_ai': []  # Extensions handled by filename pattern
            },
            'videos': {
                'movies': ['.mp4', '.mov', '.avi', '.mkv'],
                'shorts': ['.webm', '.gif'],
                'streaming': ['.m3u8', '.ts'],
                'whatsapp': [],  # Extensions handled by filename pattern in categorize_file
                'telegram': [],  # Extensions handled by filename pattern in categorize_file
                'instagram': [],  # Extensions handled by filename pattern in categorize_file
                'facebook': [],  # Extensions handled by filename pattern in categorize_file
                'youtube': []  # Extensions handled by filename pattern in categorize_file
            },
            'audio': {
                'music': ['.mp3', '.wav', '.flac', '.m4a', '.aac'],
                'voice': ['.wma', '.ogg']
            },
            'code': {
                'python': ['.py', '.pyw', '.ipynb'],
                'web': ['.html', '.css', '.js', '.php'],
                'data': ['.json', '.xml', '.yaml', '.sql'],
                'scripts': ['.sh', '.bat', '.ps1']
            },
            'archives': {
                'compressed': ['.zip', '.rar', '.7z', '.tar.gz', '.tar'],
                'disk_images': ['.iso', '.img']
            },
            'office': {
                'templates': ['.dotx', '.potx', '.xltx'],
                'outlook': ['.pst', '.ost', '.msg'],
                'database': ['.accdb', '.mdb']
            }
        }
        
        # spaCy model is injected later via set_nlp_model() once the
        # background ModelLoaderThread has successfully loaded it.
        # We never attempt to load it here to avoid triggering DLL issues
        # before the main-thread pre-warm has run.
        if self.nlp is None:
            self.ai_enabled = False
        
        # Lazy ML classifier — bootstrapped on first use (see _get_ml_classifier).
        # Using None here keeps __init__ fast; the classifier constructs itself on
        # the first file that falls through the extension map.
        self._ml_classifier: '_AIFileClassifier | None' = None
    
    def set_nlp_model(self, nlp):
        """
        Update the spaCy model after initialization.
        
        Args:
            nlp: Pre-loaded spaCy model to use for AI categorization
        """
        if nlp is not None:
            self.nlp = nlp
            self.ai_enabled = True
            logger.info("✓ spaCy model updated - AI categorization now enabled")
        


    def _get_ml_classifier(self):
        """Return the shared ML classifier, constructing it on first call.

        The constructor auto-bootstraps (no real files needed), so this is
        safe to call on any file.  Returns ``None`` if ``AIFileClassifier``
        could not be imported, keeping the whole ML path fully optional.
        """
        if not _ML_CLASSIFIER_AVAILABLE:
            return None
        if self._ml_classifier is None:
            try:
                self._ml_classifier = _AIFileClassifier()
                logger.debug("AIFileClassifier initialised and bootstrapped.")
            except Exception as e:  # pragma: no cover
                logger.warning("Could not initialise AIFileClassifier: %s", e)
                return None
        return self._ml_classifier

    def categorize_file(self, file_path):
        """Categorize a file based on its content and metadata"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        file_name = file_path.name.lower()
        
        # Check for AI-generated images by filename pattern
        ai_patterns = {
            'chatgpt': ['chatgpt', 'gpt', 'openai', 'dall-e', 'dalle', 'dall e'],
            'midjourney': ['midjourney', 'mj'],
            'stable_diffusion': ['stable diffusion', 'stablediffusion', 'sd'],
            'bing': ['bing ai', 'bing image', 'bing creator'],
            'bard': ['bard', 'google bard', 'google ai'],
            'claude': ['claude', 'anthropic'],
            'other_ai': ['ai generated', 'ai created', 'ai image', 'generated by ai']
        }
        
        if extension in ['.jpg', '.jpeg', '.png', '.webp']:
            for ai_source, patterns in ai_patterns.items():
                if any(pattern in file_name for pattern in patterns):
                    return f"ai_images/{ai_source}"
        
        # Check for social media files by filename pattern
        # WhatsApp
        if 'whatsapp' in file_name or 'wa' in file_name:
            if extension in ['.mp4', '.avi', '.3gp', '.mov']:
                return "videos/whatsapp"
            elif extension in ['.jpg', '.jpeg', '.png']:
                return "images/whatsapp"
                
        # Telegram
        if 'telegram' in file_name or 'tg' in file_name:
            if extension in ['.mp4', '.avi', '.3gp', '.mov']:
                return "videos/telegram"
            elif extension in ['.jpg', '.jpeg', '.png']:
                return "images/telegram"
                
        # Instagram
        if 'instagram' in file_name or 'ig' in file_name:
            if extension in ['.mp4', '.avi', '.3gp', '.mov']:
                return "videos/instagram"
            elif extension in ['.jpg', '.jpeg', '.png']:
                return "images/instagram"
                
        # Facebook
        if 'facebook' in file_name or 'fb' in file_name:
            if extension in ['.mp4', '.avi', '.3gp', '.mov']:
                return "videos/facebook"
            elif extension in ['.jpg', '.jpeg', '.png']:
                return "images/facebook"
                
        # YouTube
        if 'youtube' in file_name or 'yt' in file_name:
            if extension in ['.mp4', '.avi', '.mkv', '.mov']:
                return "videos/youtube"
        
        for category, subcategories in self.categories.items():
            for subcategory, extensions in subcategories.items():
                if extension in extensions:
                    return f"{category}/{subcategory}"

        
        if self._is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  
                return self._analyze_text_content(content)
            except (IOError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read text file {file_path}: {e}")

        # ---- ML confidence-gated override (last resort) ----
        # Fires only when the extension map and spaCy analysis both failed to
        # produce a confident answer.  safe_predict() returns None if the
        # bootstrap / progressive model isn't confident enough (< 0.6), so the
        # caller still gets 'misc/other' — we never silently mis-sort.
        ml = self._get_ml_classifier()
        if ml is not None:
            ml_result = ml.safe_predict(file_path, confidence_threshold=0.6)
            if ml_result:
                category = ml_result['category']
                confidence = ml_result['confidence']
                logger.debug(
                    "ML override: %s → %s (conf=%.2f)",
                    file_path.name, category, confidence
                )
                return category

        return 'misc/other'

    def _is_text_file(self, file_path):
        """Check if file is text-based"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type and mime_type.startswith('text')

    def _analyze_text_content(self, content):
        """Analyze text content using spaCy or basic pattern matching"""
        # Basic code detection patterns (works without NLP)
        code_indicators = {
            'python': ['def ', 'class ', 'import ', 'print('],
            'web': ['<html>', '<body>', 'function()', 'const '],
            'data': ['SELECT ', 'INSERT ', 'CREATE TABLE', '{', '[']
        }

        for lang, indicators in code_indicators.items():
            if any(indicator in content for indicator in indicators):
                return f'code/{lang}'
        
        # If AI is enabled, use spaCy for entity detection
        if self.ai_enabled and self.nlp:
            try:
                doc = self.nlp(content)
                if len(doc.ents) > 0:  # Has named entities
                    return 'documents/text'
            except Exception as e:
                logger.warning(f"Error during NLP analysis: {e}")
        
        # Default to text documents
        return 'documents/text'
