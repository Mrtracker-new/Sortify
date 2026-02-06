import os
import json
from pathlib import Path
import logging

class ConfigManager:
    """Manages application configuration settings"""
    def __init__(self, config_file=None):
        # Default config file location
        if config_file is None:
            self.config_file = Path(os.path.expanduser('~')) / '.sortify' / 'config.json'
        else:
            self.config_file = Path(config_file)
            
        # Create directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.config = {
            'last_training_directory': '',
            'last_watch_directory': '',
            'last_schedule_directory': '',
            'last_destination_directory': '',
            'last_file_directory': '',
            'last_model_directory': '',
            'model_path': '',
            'auto_sort_enabled': False,
            'watch_folder': '',
            'schedule_enabled': False,
            'schedule_folder': '',
            'schedule_type': 'daily',
            'schedule_hour': 0,
            'schedule_minute': 0,
            'schedule_day': 0,
            'ai_enabled': False,
            'commands_enabled': False
        }
        
        # Categories file path
        self.categories_file = self.config_file.parent / 'categories.json'
        
        # Load existing configuration if available
        self.load_config()
        
        # Load categories (separate from main config)
        self.categories = self._load_categories()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update config with loaded values
                    self.config.update(loaded_config)
                logging.info(f"Loaded configuration from {self.config_file}")
            else:
                logging.info("No configuration file found, using defaults")
                self.save_config()  # Create default config file
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            # If loading fails, save the default configuration
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value and save"""
        self.config[key] = value
        return self.save_config()
    
    def get_last_directory(self, directory_type):
        """Get the last used directory of a specific type"""
        key = f'last_{directory_type}_directory'
        return self.get(key, '')
    
    def set_last_directory(self, directory_type, path):
        """Set the last used directory of a specific type"""
        key = f'last_{directory_type}_directory'
        return self.set(key, path)
    
    def _get_default_categories(self):
        """Return comprehensive default category structure"""
        return {
            'Images': {
                'jpg': {'extensions': ['.jpg', '.jpeg', '.jfif']},
                'png': {'extensions': ['.png']},
                'gif': {'extensions': ['.gif']},
                'bmp': {'extensions': ['.bmp']},
                'webp': {'extensions': ['.webp']},
                'heic': {'extensions': ['.heic', '.heif']},
                'tiff': {'extensions': ['.tiff', '.tif']},
                'vector': {'extensions': ['.svg']},
                'raw': {'extensions': ['.raw', '.cr2', '.nef', '.arw', '.dng']},
                'screenshots': {'extensions': [], 'patterns': ['screenshot', 'screen shot', 'capture', 'snip']},
                'whatsapp': {'extensions': [], 'patterns': ['whatsapp', 'wa-', 'img-']},
                'telegram': {'extensions': [], 'patterns': ['telegram', 'tg-']},
                'instagram': {'extensions': [], 'patterns': ['instagram', 'insta-', 'ig-']},
                'facebook': {'extensions': [], 'patterns': ['facebook', 'fb-', 'fb_']},
                'twitter': {'extensions': [], 'patterns': ['twitter', 'tweet-']},
                'discord': {'extensions': [], 'patterns': ['discord', 'disc-']},
                'snapchat': {'extensions': [], 'patterns': ['snapchat', 'snap-']},
                'tiktok': {'extensions': [], 'patterns': ['tiktok', 'tt-']}
            },
            'AI_Images': {
                'chatgpt': {'extensions': [], 'patterns': ['chatgpt', 'dall-e', 'dalle', 'openai']},
                'midjourney': {'extensions': [], 'patterns': ['midjourney', 'mj_', 'mj-']},
                'stable_diffusion': {'extensions': [], 'patterns': ['stable_diffusion', 'sd-', 'stablediffusion']},
                'bing': {'extensions': [], 'patterns': ['bing', 'bing_ai']},
                'bard': {'extensions': [], 'patterns': ['bard', 'gemini']},
                'claude': {'extensions': [], 'patterns': ['claude', 'anthropic']},
                'leonardo': {'extensions': [], 'patterns': ['leonardo', 'leonardo.ai']},
                'other_ai': {'extensions': [], 'patterns': ['ai_generated', 'ai-gen', 'generated']}
            },
            'Documents': {
                'pdf': {'extensions': ['.pdf']},
                'word': {'extensions': ['.doc', '.docx', '.docm', '.dot', '.dotx', '.rtf']},
                'text': {'extensions': ['.txt', '.md', '.markdown', '.log', '.tex']},
                'ebooks': {'extensions': ['.epub', '.mobi', '.azw', '.azw3', '.fb2']},
                'notes': {'extensions': ['.one', '.onenote', '.notion']},
                'gdocs': {'extensions': [], 'patterns': ['google_docs', 'gdoc-']},
                'dropbox': {'extensions': [], 'patterns': ['dropbox', 'db-']},
                'onedrive': {'extensions': [], 'patterns': ['onedrive', 'od-']},
                'icloud': {'extensions': [], 'patterns': ['icloud']}
            },
            'Audio': {
                'music': {'extensions': ['.mp3', '.m4a', '.aac', '.ogg', '.opus']},
                'lossless': {'extensions': ['.flac', '.wav', '.alac', '.aiff', '.ape']},
                'playlists': {'extensions': ['.m3u', '.m3u8', '.pls', '.wpl']},
                'voice': {'extensions': ['.wma', '.voc', '.amr']},
                'podcasts': {'extensions': [], 'patterns': ['podcast', 'episode']},
                'recordings': {'extensions': [], 'patterns': ['recording', 'rec-', 'voice_memo']}
            },
            'Video': {
                'movies': {'extensions': ['.mp4', '.mov', '.m4v', '.mpg', '.mpeg']},
                'tv': {'extensions': ['.mkv', '.avi']},
                'mobile': {'extensions': ['.3gp', '.3g2']},
                'web': {'extensions': ['.webm', '.flv']},
                'whatsapp': {'extensions': [], 'patterns': ['whatsapp', 'wa-', 'vid-']},
                'telegram': {'extensions': [], 'patterns': ['telegram', 'tg-']},
                'instagram': {'extensions': [], 'patterns': ['instagram', 'insta-', 'ig-']},
                'facebook': {'extensions': [], 'patterns': ['facebook', 'fb-', 'fb_']},
                'youtube': {'extensions': [], 'patterns': ['youtube', 'yt-']},
                'tiktok': {'extensions': [], 'patterns': ['tiktok', 'tt-']},
                'zoom': {'extensions': [], 'patterns': ['zoom', 'zoom_']}
            },
            'Archives': {
                'zip': {'extensions': ['.zip', '.zipx']},
                'rar': {'extensions': ['.rar']},
                '7z': {'extensions': ['.7z']},
                'tar': {'extensions': ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz']},
                'compressed': {'extensions': ['.gz', '.bz2', '.xz', '.z']},
                'disk': {'extensions': ['.iso', '.dmg', '.img']},
                'backups': {'extensions': ['.bak', '.backup'], 'patterns': ['backup', 'bkp-']}
            },
            'Code': {
                'python': {'extensions': ['.py', '.pyw', '.ipynb', '.pyx']},
                'web': {'extensions': ['.html', '.htm', '.css', '.scss', '.sass', '.less']},
                'javascript': {'extensions': ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']},
                'java': {'extensions': ['.java', '.jar', '.class']},
                'cpp': {'extensions': ['.c', '.cpp', '.cc', '.h', '.hpp', '.hxx']},
                'csharp': {'extensions': ['.cs', '.cshtml', '.xaml']},
                'php': {'extensions': ['.php', '.phtml']},
                'ruby': {'extensions': ['.rb', '.erb']},
                'go': {'extensions': ['.go']},
                'rust': {'extensions': ['.rs']},
                'swift': {'extensions': ['.swift']},
                'kotlin': {'extensions': ['.kt', '.kts']},
                'scripts': {'extensions': ['.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd']},
                'data': {'extensions': ['.json', '.xml', '.yaml', '.yml', '.toml', '.csv']}
            },
            'Applications': {
                'windows': {'extensions': ['.exe', '.msi', '.dll']},
                'mac': {'extensions': ['.app', '.dmg', '.pkg']},
                'linux': {'extensions': ['.deb', '.rpm', '.AppImage', '.snap']},
                'mobile': {'extensions': ['.apk', '.ipa', '.xapk']},
                'portable': {'extensions': ['.jar']},
                'installers': {'extensions': [], 'patterns': ['setup', 'installer', 'install']}
            },
            'Design': {
                'photoshop': {'extensions': ['.psd', '.psb']},
                'illustrator': {'extensions': ['.ai', '.eps']},
                'vector': {'extensions': ['.svg', '.svgz']},
                'cad': {'extensions': ['.dwg', '.dxf', '.dwf']},
                '3d': {'extensions': ['.obj', '.fbx', '.blend', '.3ds', '.max', '.ma', '.mb', '.stl', '.ply']},
                'fonts': {'extensions': ['.ttf', '.otf', '.woff', '.woff2', '.eot']},
                'figma': {'extensions': ['.fig']},
                'sketch': {'extensions': ['.sketch']},
                'xd': {'extensions': ['.xd']}
            },
            'Databases': {
                'sqlite': {'extensions': ['.db', '.sqlite', '.sqlite3', '.db3']},
                'sql': {'extensions': ['.sql']},
                'access': {'extensions': ['.mdb', '.accdb']},
                'other': {'extensions': ['.dbf', '.sdf', '.mdf']}
            },
            'Spreadsheets': {
                'excel': {'extensions': ['.xlsx', '.xls', '.xlsm', '.xlsb']},
                'csv': {'extensions': ['.csv', '.tsv']},
                'ods': {'extensions': ['.ods']},
                'numbers': {'extensions': ['.numbers']},
                'gsheets': {'extensions': [], 'patterns': ['google_sheets', 'gsheet-']}
            },
            'Presentations': {
                'powerpoint': {'extensions': ['.ppt', '.pptx', '.pps', '.ppsx']},
                'keynote': {'extensions': ['.key']},
                'odp': {'extensions': ['.odp']},
                'gslides': {'extensions': [], 'patterns': ['google_slides', 'gslide-']}
            },
            'Email': {
                'outlook': {'extensions': ['.msg', '.oft', '.pst', '.ost']},
                'eml': {'extensions': ['.eml', '.emlx']},
                'mbox': {'extensions': ['.mbox']},
                'other': {'extensions': ['.vcf', '.ics']}
            },
            'System': {
                'config': {'extensions': ['.ini', '.conf', '.config', '.cfg']},
                'env': {'extensions': ['.env', '.env.local', '.env.production']},
                'logs': {'extensions': ['.log', '.log.1', '.log.2']},
                'certificates': {'extensions': ['.pem', '.key', '.crt', '.cer', '.p12', '.pfx']},
                'registry': {'extensions': ['.reg']},
                'shortcuts': {'extensions': ['.lnk', '.url']}
            },
            'Virtual_Machines': {
                'vmware': {'extensions': ['.vmdk', '.vmx', '.vmxf', '.nvram']},
                'virtualbox': {'extensions': ['.vdi', '.vbox', '.vbox-prev']},
                'vagrant': {'extensions': ['.box'], 'patterns': ['vagrantfile']},
                'docker': {'extensions': [], 'patterns': ['dockerfile', 'docker-compose']},
                'qemu': {'extensions': ['.qcow2', '.qed']},
                'ova': {'extensions': ['.ova', '.ovf']}
            },
            'Torrents': {
                'torrent': {'extensions': ['.torrent']},
                'magnet': {'extensions': [], 'patterns': ['magnet']}
            },
            'Subtitles': {
                'srt': {'extensions': ['.srt']},
                'sub': {'extensions': ['.sub']},
                'ass': {'extensions': ['.ass', '.ssa']},
                'vtt': {'extensions': ['.vtt']},
                'idx': {'extensions': ['.idx']}
            },
            'Uncategorized': {
                'other': {'extensions': ['*']}
            }
        }
    
    def _load_categories(self):
        """Load categories from file or return defaults"""
        try:
            if self.categories_file.exists():
                with open(self.categories_file, 'r') as f:
                    categories = json.load(f)
                logging.info(f"Loaded categories from {self.categories_file}")
                return categories
            else:
                logging.info("No categories file found, using defaults")
                # Create default categories file
                default_categories = self._get_default_categories()
                self.save_categories(default_categories)
                return default_categories
        except Exception as e:
            logging.error(f"Error loading categories: {e}")
            # If loading fails, return default categories
            return self._get_default_categories()
    
    def save_categories(self, categories=None):
        """Save categories to file"""
        try:
            if categories is None:
                categories = self.categories
            
            with open(self.categories_file, 'w') as f:
                json.dump(categories, f, indent=2)
            logging.info(f"Saved categories to {self.categories_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving categories: {e}")
            return False
    
    def get_categories(self):
        """Get current category structure"""
        return self.categories