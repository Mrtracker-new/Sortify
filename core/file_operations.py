import os
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QFileDialog
from .history import HistoryManager
from .safety_manager import SafetyManager

class FileOperations:
    def setup_organization(self, parent=None):
        """
        Prompt user for organization folder details and validate the path using GUI dialogs
        
        Args:
            parent: Parent widget for the dialogs
            
        Returns:
            tuple: (base_path, folder_name) containing validated path and folder name
        """
        try:
            # Step 1: Choose Location
            location_options = [
                "Desktop (~/Desktop)",
                "Documents (~/Documents)",
                "Custom Path",
                "Root Drive (C:/)"
            ]
            
            location, ok = QInputDialog.getItem(
                parent,
                "Organization Folder Location",
                "Where would you like to create your organization folder?",
                location_options,
                0,  # Default to first option
                False  # Not editable
            )
            
            if not ok:
                return None, None
                
            if "Desktop" in location:
                base_path = os.path.expanduser("~/Desktop")
            elif "Documents" in location:
                base_path = os.path.expanduser("~/Documents")
            elif "Custom Path" in location:
                base_path = QFileDialog.getExistingDirectory(
                    parent,
                    "Select Custom Location",
                    os.path.expanduser("~")
                )
                if not base_path:  # User cancelled
                    return None, None
            else:  # Root Drive
                base_path = "C:/"
            
            # Step 2: Name Your Organization Folder
            name_options = [
                "Organized Files",
                "My Files",
                "File System",
                "Custom Name"
            ]
            
            name_choice, ok = QInputDialog.getItem(
                parent,
                "Organization Folder Name",
                "Choose a name for your organization folder:",
                name_options,
                0,  # Default to first option
                False  # Not editable
            )
            
            if not ok:
                return None, None
                
            if name_choice == "Custom Name":
                folder_name, ok = QInputDialog.getText(
                    parent,
                    "Custom Folder Name",
                    "Enter your custom folder name:"
                )
                if not ok or not folder_name:
                    return None, None
            else:
                folder_name = name_choice
            
            # Validate the path
            full_path = Path(base_path) / folder_name
            
            if full_path.exists():
                response = QMessageBox.question(
                    parent,
                    "Folder Already Exists",
                    f"Folder '{folder_name}' already exists at {base_path}. Use existing folder?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if response != QMessageBox.StandardButton.Yes:
                    return self.setup_organization(parent)  # Try again
            else:
                # Test if we can create the folder
                try:
                    full_path.mkdir(parents=True)
                    full_path.rmdir()  # Remove the test directory
                except PermissionError:
                    QMessageBox.critical(
                        parent,
                        "Permission Error",
                        f"No permission to create folder at {base_path}\nPlease choose a different location."
                    )
                    return self.setup_organization(parent)  # Try again
                except Exception as e:
                    QMessageBox.critical(
                        parent,
                        "Error",
                        f"Error creating folder: {str(e)}\nPlease choose a different location."
                    )
                    return self.setup_organization(parent)  # Try again
            
            QMessageBox.information(
                parent,
                "Success",
                f"Organization folder will be created at: {full_path}"
            )
            
            return base_path, folder_name
            
        except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again.")

    def __init__(self, base_path=None, folder_name=None, safety_config=None, dry_run=False, skip_confirmations=False):
        """
        Initialize FileOperations with customizable base path and folder name
        
        Args:
            base_path (str or Path, optional): Base directory path. If None, will prompt user
            folder_name (str, optional): Name of the organization folder. If None, will prompt user
            safety_config (dict, optional): Configuration for safety features
            dry_run (bool): If True, only preview operations without executing them
            skip_confirmations (bool): If True, skip all confirmation dialogs
        """
        
        # Store dry-run mode state
        self.dry_run = dry_run
        
        # Import dry-run manager only if needed
        if self.dry_run:
            from .dry_run import DryRunManager
            self.dry_run_manager = DryRunManager()
        else:
            self.dry_run_manager = None
        
        if base_path is None or folder_name is None:
            # Skip GUI dialogs in dry-run mode
            if not dry_run:
                base_path, folder_name = self.setup_organization(None)
            
            # If user cancelled the dialog or dry-run mode, use default values
            if base_path is None or folder_name is None:
                base_path = str(Path.home() / "Documents")
                folder_name = "Organized Files"
        
        self.base_dir = Path(base_path) / folder_name
        self.history = HistoryManager()
        
        # Pass skip_confirmations to SafetyManager
        if safety_config is None:
            safety_config = {}
        safety_config['skip_confirmations'] = skip_confirmations
        self.safety = SafetyManager(config=safety_config)
        self.session_active = False
        
        
        # Only create directory in non-dry-run mode
        if not dry_run:
            try:
                self.base_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                raise PermissionError(
                    f"Unable to create folder at {self.base_dir}. Please ensure you have "
                    "appropriate permissions or choose a different location."
                )

        
        self.categories = {
            'documents': ['word', 'pdf', 'text', 'ebooks'],
            'images': ['photos', 'screenshots', 'artwork', 'jpg', 'png', 'gif', 'bmp', 'webp', 'heic', 'tiff', 'vector', 'raw', 'whatsapp', 'telegram', 'instagram', 'facebook', 'ai'],
            'ai_images': ['chatgpt', 'midjourney', 'stable_diffusion', 'bing', 'bard', 'claude', 'other_ai'],
            'videos': ['movies', 'recordings', 'tutorials'],
            'audio': ['music', 'podcasts', 'recordings'],
            'code': ['python', 'javascript', 'web', 'data'],
            'archives': ['compressed', 'backups', 'installers'],
            'office': ['templates', 'spreadsheets', 'presentations'],
            'downloads': ['software', 'media', 'temporary'],
            'personal': ['documents', 'finance', 'records'],
            'misc': ['other']
        }

    def create_category_folders(self):
        """Create all category folders"""
        try:
            for category, subcategories in self.categories.items():
                category_path = self.base_dir / category
                category_path.mkdir(exist_ok=True)
                
                for subcategory in subcategories:
                    subcategory_path = category_path / subcategory
                    subcategory_path.mkdir(exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating category folders: {e}")
            return False
    
    def start_operations(self):
        """Start a new batch of file operations with session tracking"""
        if not self.session_active:
            self.history.start_session()
            self.session_active = True
    
    def finalize_operations(self):
        """Finalize the current batch of operations and end session"""
        if self.session_active:
            self.history.end_session()
            self.session_active = False
            # Clean up old backups if enabled
            self.safety.cleanup_old_backups()

    def copy_file(self, source_path, category_path):
        """Copy file to appropriate category folder
        
        Args:
            source_path (str or Path): Path to the source file
            category_path (str): Category path in format 'category/subcategory'
            
        Returns:
            Path: Destination path where the file was copied (or would be copied in dry-run mode)
        """
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {source_path}")

            # Parse the category path
            if '/' in category_path:
                category, subcategory = category_path.split('/')
                dest_dir = self.base_dir / category / subcategory
            else:
                # If no subcategory is specified, use the category as the destination directory
                dest_dir = self.base_dir / category_path
                
            dest_path = dest_dir / source_path.name

            # Handle filename conflicts
            if dest_path.exists():
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{dest_path.stem}_{counter}{dest_path.suffix}"
                    counter += 1
            
            # DRY-RUN MODE: Only record the operation, don't execute
            if self.dry_run:
                self.dry_run_manager.add_operation('copy', source_path, dest_path, category_path)
                return dest_path
            
            # NORMAL MODE: Execute the operation
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source_path), str(dest_path))
            self.history.log_operation(str(source_path), str(dest_path), operation_type="copy")
            return dest_path
        except Exception as e:
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="copy", metadata={'error': str(e)})
            raise

    def move_file(self, source_path, category_path, parent=None, skip_confirmation=False):
        """Move file to appropriate category folder with optional safety confirmation
        
        Args:
            source_path (str or Path): Path to the source file
            category_path (str): Category path in format 'category/subcategory'
            parent (QWidget, optional): Parent widget for confirmation dialog
            skip_confirmation (bool): Skip safety confirmation if True
            
        Returns:
            Path: Destination path where the file was moved (or would be moved in dry-run mode)
        """
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {source_path}")
            
            # Parse the category path
            if '/' in category_path:
                category, subcategory = category_path.split('/')
                dest_dir = self.base_dir / category / subcategory
            else:
                # If no subcategory is specified, use the category as the destination directory
                dest_dir = self.base_dir / category_path
                
            dest_path = dest_dir / source_path.name

            # Handle filename conflicts
            if dest_path.exists():
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{dest_path.stem}_{counter}{dest_path.suffix}"
                    counter += 1
            
            # DRY-RUN MODE: Only record the operation, don't execute
            if self.dry_run:
                self.dry_run_manager.add_operation('move', source_path, dest_path, category_path)
                return dest_path
            
            # NORMAL MODE: Execute the operation
            # Safety confirmation (if enabled)
            if not skip_confirmation:
                if not self.safety.confirm_operation('move', source_path, parent):
                    return None  # User cancelled
            
            # Optional backup before move (if enabled)
            self.safety.create_backup(source_path)

            # Create destination directory
            dest_dir.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source_path), str(dest_path))
            self.history.log_operation(str(source_path), str(dest_path), operation_type="move")
            return dest_path
        except Exception as e:
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="move", metadata={'error': str(e)})
            raise

    def rename_file(self, file_path, new_name=None, options=None):
        """
        Enhanced file renaming with multiple options
        
        Args:
            file_path (str): Path to the file
            new_name (str, optional): New name for the file
            options (dict, optional): Dictionary of renaming options:
                - add_date (bool): Add date prefix (default: False)
                - add_time (bool): Add time prefix (default: False)
                - date_format (str): Custom date format (default: "%Y%m%d")
                - case (str): 'lower', 'upper', 'title', or None
                - remove_spaces (bool): Replace spaces with underscores
                - add_sequence (bool): Add sequence number for similar files
                - custom_prefix (str): Add custom prefix
                - custom_suffix (str): Add custom suffix
                - remove_special_chars (bool): Remove special characters
        
        Returns:
            Path: New file path
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            
            default_options = {
                'add_date': False,
                'add_time': False,
                'date_format': "%Y%m%d",
                'case': None,
                'remove_spaces': False,
                'add_sequence': True,
                'custom_prefix': '',
                'custom_suffix': '',
                'remove_special_chars': False
            }

            
            options = {**default_options, **(options or {})}

            
            original_name = file_path.stem
            extension = file_path.suffix
            final_name = new_name if new_name else original_name

            
            if options['remove_special_chars']:
                final_name = ''.join(c for c in final_name if c.isalnum() or c in '- _')

            if options['remove_spaces']:
                final_name = final_name.replace(' ', '_')

            if options['case']:
                if options['case'] == 'lower':
                    final_name = final_name.lower()
                elif options['case'] == 'upper':
                    final_name = final_name.upper()
                elif options['case'] == 'title':
                    final_name = final_name.title()

            
            prefix_parts = []
            
            if options['add_date'] or options['add_time']:
                if options['add_date'] and options['add_time']:
                    date_str = datetime.now().strftime(f"{options['date_format']}_%H%M%S")
                elif options['add_date']:
                    date_str = datetime.now().strftime(options['date_format'])
                else:
                    date_str = datetime.now().strftime("%H%M%S")
                prefix_parts.append(date_str)

            
            if options['custom_prefix']:
                prefix_parts.append(options['custom_prefix'])

            
            if prefix_parts:
                final_name = f"{('_'.join(prefix_parts))}_{final_name}"

            
            if options['custom_suffix']:
                final_name = f"{final_name}_{options['custom_suffix']}"

            
            new_path = file_path.parent / f"{final_name}{extension}"

            
            if options['add_sequence'] and new_path.exists():
                counter = 1
                while new_path.exists():
                    sequence_name = f"{final_name}_{counter}{extension}"
                    new_path = file_path.parent / sequence_name
                    counter += 1

            
            file_path.rename(new_path)

            
            metadata = {
                'original_name': str(file_path),
                'new_name': str(new_path),
                'options_used': options
            }
            self.history.log_operation(
                str(file_path),
                str(new_path),
                operation_type="rename",
                metadata=metadata
            )

            return new_path

        except Exception as e:
            error_msg = f"Error renaming file: {str(e)}"
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise RuntimeError(error_msg)

    def batch_rename(self, file_paths, pattern=None, options=None):
        """
        Rename multiple files at once
        
        Args:
            file_paths (list): List of file paths to rename
            pattern (str, optional): Naming pattern with placeholders:
                {n} - sequential number
                {date} - current date
                {time} - current time
                {orig} - original filename
            options (dict, optional): Same options as rename_file
        
        Returns:
            dict: Mapping of original paths to new paths
        """
        results = {}
        
        try:
            for index, file_path in enumerate(file_paths, 1):
                if pattern:
                    
                    new_name = pattern.format(
                        n=index,
                        date=datetime.now().strftime("%Y%m%d"),
                        time=datetime.now().strftime("%H%M%S"),
                        orig=Path(file_path).stem
                    )
                    new_path = self.rename_file(file_path, new_name, options)
                else:
                    new_path = self.rename_file(file_path, None, options)
                
                results[str(file_path)] = str(new_path)
                
            return results
            
        except Exception as e:
            error_msg = f"Error in batch rename: {str(e)}"
            self.history.log_operation(
                "batch_rename",
                "failed",
                operation_type="batch_rename",
                metadata={'error': error_msg, 'files': file_paths}
            )
            raise RuntimeError(error_msg)

    def categorize_file(self, file_path):
        """
        Categorize a file based on its extension, content, and metadata
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: category/subcategory path
        """
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower().replace('.', '')
        file_name = file_path.name.lower()
        
        # Enhanced extension mapping with more file types
        ext_mapping = {
            # Documents
            'pdf': 'documents/pdf',
            'doc': 'documents/word',
            'docx': 'documents/word',
            'txt': 'documents/text',
            'rtf': 'documents/text',
            'md': 'documents/text',
            'epub': 'documents/ebooks',
            'mobi': 'documents/ebooks',
            'azw': 'documents/ebooks',
            'azw3': 'documents/ebooks',
            'log': 'documents/text',
            'tex': 'documents/text',
            
            # Images - Enhanced with specific format subcategories
            'jpg': 'images/jpg',
            'jpeg': 'images/jpg',
            'png': 'images/png',
            'gif': 'images/gif',
            'bmp': 'images/bmp',
            'webp': 'images/webp',
            'heic': 'images/heic',
            'heif': 'images/heic',
            'jfif': 'images/jpg',
            'svg': 'images/vector',
            'ai': 'images/vector',
            'eps': 'images/vector',
            'raw': 'images/raw',
            'cr2': 'images/raw',
            'nef': 'images/raw',
            'arw': 'images/raw',
            'dng': 'images/raw',
            'tiff': 'images/tiff',
            'tif': 'images/tiff',
            
            # Videos
            'mp4': 'videos/movies',
            'avi': 'videos/movies',
            'mkv': 'videos/movies',
            'mov': 'videos/movies',
            'wmv': 'videos/movies',
            'webm': 'videos/movies',
            'flv': 'videos/movies',
            'm4v': 'videos/movies',
            'mpg': 'videos/movies',
            'mpeg': 'videos/movies',
            '3gp': 'videos/mobile',
            '3g2': 'videos/mobile',
            
            # Audio
            'mp3': 'audio/music',
            'wav': 'audio/music',
            'flac': 'audio/lossless',
            'm4a': 'audio/music',
            'aac': 'audio/music',
            'ogg': 'audio/music',
            'wma': 'audio/music',
            'opus': 'audio/voice',
            'aiff': 'audio/lossless',
            'alac': 'audio/lossless',
            'm3u': 'audio/playlists',
            'pls': 'audio/playlists',
            
            # Code
            'py': 'code/python',
            'pyw': 'code/python',
            'ipynb': 'code/python',
            'js': 'code/javascript',
            'jsx': 'code/javascript',
            'ts': 'code/javascript',
            'tsx': 'code/javascript',
            'html': 'code/web',
            'htm': 'code/web',
            'css': 'code/web',
            'scss': 'code/web',
            'sass': 'code/web',
            'less': 'code/web',
            'php': 'code/web',
            'java': 'code/java',
            'jar': 'code/java',
            'class': 'code/java',
            'cpp': 'code/cpp',
            'c': 'code/cpp',
            'h': 'code/cpp',
            'hpp': 'code/cpp',
            'cs': 'code/csharp',
            'go': 'code/other',
            'rs': 'code/other',
            'rb': 'code/other',
            'swift': 'code/other',
            'kt': 'code/other',
            'json': 'code/data',
            'xml': 'code/data',
            'yaml': 'code/data',
            'yml': 'code/data',
            'toml': 'code/data',
            'sql': 'code/data',
            'sh': 'code/scripts',
            'bash': 'code/scripts',
            'ps1': 'code/scripts',
            'bat': 'code/scripts',
            'cmd': 'code/scripts',
            
            # Archives
            'zip': 'archives/compressed',
            'rar': 'archives/compressed',
            '7z': 'archives/compressed',
            'tar': 'archives/compressed',
            'gz': 'archives/compressed',
            'bz2': 'archives/compressed',
            'xz': 'archives/compressed',
            'tgz': 'archives/compressed',
            'iso': 'archives/disk',
            'dmg': 'archives/disk',
            
            # Office
            'xlsx': 'office/spreadsheets',
            'xls': 'office/spreadsheets',
            'csv': 'office/spreadsheets',
            'ods': 'office/spreadsheets',
            'pptx': 'office/presentations',
            'ppt': 'office/presentations',
            'pps': 'office/presentations',
            'ppsx': 'office/presentations',
            'odp': 'office/presentations',
            'dotx': 'office/templates',
            'potx': 'office/templates',
            'xltx': 'office/templates',
            'pst': 'office/outlook',
            'ost': 'office/outlook',
            'msg': 'office/outlook',
            'accdb': 'office/database',
            'mdb': 'office/database',
            
            # Applications
            'exe': 'applications/windows',
            'msi': 'applications/windows',
            'dll': 'applications/windows',
            'app': 'applications/mac',
            'pkg': 'applications/mac',
            'deb': 'applications/linux',
            'rpm': 'applications/linux',
            'appimage': 'applications/linux',
            'apk': 'applications/mobile',
            'ipa': 'applications/mobile',
            
            # Design
            'eps': 'design/vector',
            'dwg': 'design/cad',
            'dxf': 'design/cad',
            'stl': 'design/3d',
            'obj': 'design/3d',
            'fbx': 'design/3d',
            'blend': 'design/3d',
            '3ds': 'design/3d',
            'ttf': 'design/fonts',
            'otf': 'design/fonts',
            'woff': 'design/fonts',
            'woff2': 'design/fonts',
        }
        
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
        
        if file_ext in ['jpg', 'jpeg', 'png', 'webp']:
            for ai_source, patterns in ai_patterns.items():
                if any(pattern in file_name for pattern in patterns):
                    return f"ai_images/{ai_source}"
        
        # Check for social media files by filename pattern
        # WhatsApp
        if 'whatsapp' in file_name or 'wa' in file_name:
            if file_ext in ['mp4', 'avi', '3gp', 'mov']:
                return 'videos/whatsapp'
            elif file_ext in ['jpg', 'jpeg', 'png']:
                return 'images/whatsapp'
        
        # Telegram
        if 'telegram' in file_name or 'tg' in file_name:
            if file_ext in ['mp4', 'avi', '3gp', 'mov']:
                return 'videos/telegram'
            elif file_ext in ['jpg', 'jpeg', 'png']:
                return 'images/telegram'
        
        # Instagram
        if 'instagram' in file_name or 'ig' in file_name:
            if file_ext in ['mp4', 'avi', '3gp', 'mov']:
                return 'videos/instagram'
            elif file_ext in ['jpg', 'jpeg', 'png']:
                return 'images/instagram'
        
        # Facebook
        if 'facebook' in file_name or 'fb' in file_name:
            if file_ext in ['mp4', 'avi', '3gp', 'mov']:
                return 'videos/facebook'
            elif file_ext in ['jpg', 'jpeg', 'png']:
                return 'images/facebook'
        
        # YouTube
        if 'youtube' in file_name or 'yt' in file_name:
            if file_ext in ['mp4', 'avi', 'mkv', 'mov']:
                return 'videos/youtube'
        
        # Try to categorize by extension first
        category_path = ext_mapping.get(file_ext, None)
        
        # If extension not found, try to categorize by content patterns
        if category_path is None:
            # Check if it's a text file we can analyze
            if self._is_text_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # Read first 1000 chars
                        
                        # Check for code patterns
                        if any(pattern in content for pattern in ['def ', 'class ', 'import ', 'function', 'var ', 'const ']):
                            category_path = 'code/other'
                        # Check for data patterns
                        elif any(pattern in content for pattern in ['{', '[', '<html>', '<xml>', 'SELECT ', 'CREATE TABLE']):
                            category_path = 'code/data'
                        # Default to text documents
                        else:
                            category_path = 'documents/text'
                except:
                    # If we can't read the file, use misc category
                    category_path = 'misc/other'
            else:
                # Use filename patterns as a last resort
                if any(pattern in file_name for pattern in ['screenshot', 'screen', 'capture']):
                    category_path = 'images/screenshots'
                elif any(pattern in file_name for pattern in ['invoice', 'receipt', 'bill', 'statement']):
                    category_path = 'documents/financial'
                elif any(pattern in file_name for pattern in ['backup', 'bak', 'old', 'archive']):
                    category_path = 'archives/backups'
                elif any(pattern in file_name for pattern in ['install', 'setup']):
                    category_path = 'applications/installers'
                else:
                    category_path = 'misc/other'
        
        return category_path
        
    def _is_text_file(self, file_path):
        """Check if file is likely a text file based on extension
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file has a known text extension, False otherwise
        """
        text_extensions = [
            # Documentation formats
            '.txt', '.md', '.rst', '.rtf', '.tex', '.adoc', '.wiki',
            # Data formats
            '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            # Web formats
            '.html', '.htm', '.css', '.scss', '.sass', '.less', '.js', '.jsx', '.ts', '.tsx',
            # Programming languages
            '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.rb', '.pl', '.swift',
            '.go', '.rs', '.kt', '.scala', '.sh', '.bash', '.ps1', '.bat', '.sql',
            # Log and config files
            '.log', '.properties', '.env'
        ]
        return file_path.suffix.lower() in text_extensions

# FileOrganizationApp class and related code removed as it's redundant with the PyQt6 implementation
