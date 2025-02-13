import spacy
import os
from pathlib import Path
import mimetypes

class FileCategorizationAI:
    def __init__(self):
        
        self.nlp = spacy.load('en_core_web_sm')
        
        
        self.categories = {
            'documents': {
                'word': ['.doc', '.docx', '.rtf', '.odt'],
                'excel': ['.xls', '.xlsx', '.csv', '.ods'],
                'powerpoint': ['.ppt', '.pptx', '.odp'],
                'pdf': ['.pdf'],
                'text': ['.txt', '.md', '.log']
            },
            'images': {
                'raster': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
                'vector': ['.svg', '.ai', '.eps'],
                'raw': ['.raw', '.cr2', '.nef', '.arw']
            },
            'videos': {
                'movies': ['.mp4', '.mov', '.avi', '.mkv'],
                'shorts': ['.webm', '.gif'],
                'streaming': ['.m3u8', '.ts']
            },
            'audio': {
                'music': ['.mp3', '.wav', '.flac', '.m4a', '.aac'],
                'voice': ['.aac', '.wma', '.ogg']
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

    def categorize_file(self, file_path):
        """Categorize a file based on its content and metadata"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        
        for category, subcategories in self.categories.items():
            for subcategory, extensions in subcategories.items():
                if extension in extensions:
                    return f"{category}/{subcategory}"

        
        if self._is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  
                return self._analyze_text_content(content)
            except:
                pass

        return 'misc/other'  

    def _is_text_file(self, file_path):
        """Check if file is text-based"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type and mime_type.startswith('text')

    def _analyze_text_content(self, content):
        """Analyze text content using spaCy"""
        doc = self.nlp(content)
        
        
        code_indicators = {
            'python': ['def ', 'class ', 'import ', 'print('],
            'web': ['<html>', '<body>', 'function()', 'const '],
            'data': ['SELECT ', 'INSERT ', 'CREATE TABLE', '{', '[']
        }

        for lang, indicators in code_indicators.items():
            if any(indicator in content for indicator in indicators):
                return f'code/{lang}'

        
        if len(doc.ents) > 0:  
            return 'documents/text'
            
        return 'documents/text'  
