import spacy
import os
from pathlib import Path
import mimetypes
import sys
import importlib.util
import logging

logger = logging.getLogger('Sortify')

class FileCategorizationAI:
    def __init__(self):
        self.nlp = None
        self.ai_enabled = False
        
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
        
        # Try to load spaCy model, but don't fail if it's not available
        try:
            logger.info("Attempting to load spaCy model")
            self.nlp = spacy.load('en_core_web_sm')
            self.ai_enabled = True
            logger.info("✓ spaCy model loaded - AI categorization enabled")
        except OSError as e:
            logger.warning(f"spaCy model not available: {e}")
            logger.info("Continuing with basic pattern-based categorization")
            self.ai_enabled = False
        except Exception as e:
            logger.warning(f"Unexpected error loading spaCy: {e}")
            logger.info("Continuing with basic pattern-based categorization")
            self.ai_enabled = False
        


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
