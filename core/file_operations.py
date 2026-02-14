import os
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QFileDialog
from .history import HistoryManager
from .safety_manager import SafetyManager
from .duplicate_finder import DuplicateFinder
import logging
import concurrent.futures
import threading

# Create module-specific logger
logger = logging.getLogger('Sortify.FileOperations')

# Shared thread pool for I/O operations (initialized lazily)
_io_executor = None
_executor_lock = threading.Lock()

def _timeout_wrapper(func, args=(), kwargs=None, timeout=5.0, default=None):
    """
    Execute a function with a timeout using threading.
    
    This is a Windows-compatible timeout wrapper since signal.alarm() is not available.
    If the function doesn't complete within the timeout, raises TimeoutError.
    
    Args:
        func: Function to execute
        args: Tuple of positional arguments
        kwargs: Dict of keyword arguments
        timeout: Maximum time to wait in seconds (default: 5.0)
        default: Default value to return on timeout (if None, raises TimeoutError)
    
    Returns:
        Result of the function call
        
    Raises:
        TimeoutError: If function execution exceeds timeout
    """
    if kwargs is None:
        kwargs = {}
    
    result = [default]  # Mutable container to store result
    exception = [None]  # Store any exception that occurs
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        # Note: We can't forcefully kill the thread in Python, but we can return/raise
        # The thread will eventually complete, but we don't wait for it
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]

def get_io_executor():
    """Get or create the shared I/O executor for non-blocking file operations"""
    global _io_executor
    if _io_executor is None:
        with _executor_lock:
            if _io_executor is None:
                # Use up to 4 threads for I/O operations
                _io_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix='FileIO'
                )
    return _io_executor

def _read_file_sync(file_path, max_chars=1000, timeout=5.0):
    """
    Synchronous file reading helper with timeout enforcement - runs in thread pool
    
    This function prevents indefinite blocking when reading from:
    - Disconnected network mounts
    - Slow network drives  
    - Hung file handles
    - Unresponsive disks
    
    Args:
        file_path: Path object to read
        max_chars: Maximum characters to read (default: 1000)
        timeout: Maximum time to wait for file read in seconds (default: 5.0)
        
    Returns:
        str: File content (up to max_chars)
        
    Raises:
        TimeoutError: If file read exceeds timeout duration
        OSError: If file cannot be opened or read
        UnicodeDecodeError: If file content cannot be decoded as UTF-8
    """
    def _do_read():
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(max_chars)
    
    try:
        return _timeout_wrapper(_do_read, timeout=timeout)
    except TimeoutError:
        # Re-raise with more context about the specific file
        raise TimeoutError(
            f"Timeout reading file '{file_path.name}' after {timeout} seconds. "
            f"The file may be on a slow network drive or the disk may be unresponsive."
        )


class FileOperations:
    # Security: Blacklist of sensitive directories that should never be accessed
    # These directories typically contain credentials, keys, or security-critical configuration
    SENSITIVE_DIRS = {
        '.ssh',         # SSH keys and configuration
        '.gnupg',       # GPG keys
        '.config',      # Application configurations (may contain credentials)
        '.aws',         # AWS credentials
        '.azure',       # Azure credentials
        '.gcp',         # Google Cloud credentials
        '.kube',        # Kubernetes configuration and credentials
        '.docker',      # Docker credentials
        'AppData',      # Windows application data (may contain credentials)
        '.password',    # Password stores
        '.cert',        # Certificate stores
        '.key',         # Private key stores
        '.gpg',         # GPG alternative location
        '.local',       # Local application data (may contain sensitive info)
        '.mozilla',     # Firefox profiles (may contain saved passwords)
        '.thunderbird', # Thunderbird profiles
    }
    
    def setup_organization(self, parent=None, max_attempts=3):
        """
        Prompt user for organization folder details and validate the path using GUI dialogs
        
        Args:
            parent: Parent widget for the dialogs
            max_attempts: Maximum number of attempts to set up organization (default: 3)
            
        Returns:
            tuple: (base_path, folder_name) containing validated path and folder name, or (None, None) if failed
        """
        for attempt in range(max_attempts):
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
                        continue  # Try again
                else:
                    # Test if we can create the folder
                    try:
                        full_path.mkdir(parents=True)
                        full_path.rmdir()  # Remove the test directory
                    except PermissionError:
                        if attempt == max_attempts - 1:
                            QMessageBox.critical(
                                parent,
                                "Error",
                                "Unable to create folder after multiple attempts.\nPlease check your permissions."
                            )
                            return None, None
                        QMessageBox.critical(
                            parent,
                            "Permission Error",
                            f"No permission to create folder at {base_path}\nPlease choose a different location."
                        )
                        continue  # Try again
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            QMessageBox.critical(
                                parent,
                                "Error",
                                f"Unable to create folder after multiple attempts.\nLast error: {str(e)}"
                            )
                            return None, None
                        QMessageBox.critical(
                            parent,
                            "Error",
                            f"Error creating folder: {str(e)}\nPlease choose a different location."
                        )
                        continue  # Try again
                
                QMessageBox.information(
                    parent,
                    "Success",
                    f"Organization folder will be created at: {full_path}"
                )
                
                return base_path, folder_name
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    QMessageBox.critical(
                        parent,
                        "Error",
                        f"Setup failed after {max_attempts} attempts.\nError: {str(e)}"
                    )
                    return None, None
                logger.error(f"Error: {str(e)}")
                logger.info("Please try again.")
                continue
        
        # If we've exhausted all attempts without returning
        return None, None

    def __init__(self, base_path=None, folder_name=None, safety_config=None, dry_run=False, skip_confirmations=False, allowed_dirs=None, config_manager=None):
        """
        Initialize FileOperations with customizable base path and folder name
        
        Args:
            base_path (str or Path, optional): Base directory path. Required for non-dry-run mode.
            folder_name (str, optional): Name of the organization folder. Required for non-dry-run mode.
            safety_config (dict, optional): Configuration for safety features
            dry_run (bool): If True, only preview operations without executing them
            skip_confirmations (bool): If True, skip all confirmation dialogs
            allowed_dirs (list, optional): List of additional allowed directories for file operations
            config_manager (ConfigManager, optional): Configuration manager for loading categories
            
        Raises:
            ValueError: If base_path or folder_name are None in non-dry-run mode
        """
        
        # Store dry-run mode state
        self.dry_run = dry_run
        
        # Import dry-run manager only if needed
        if self.dry_run:
            from .dry_run import DryRunManager
            self.dry_run_manager = DryRunManager()
        else:
            self.dry_run_manager = None
        
        # Handle None values based on mode
        if base_path is None or folder_name is None:
            if dry_run:
                # Dry-run mode: Use safe defaults
                base_path = str(Path.home() / "Documents")
                folder_name = "Organized Files"
            else:
                # Non-dry-run mode: FAIL FAST
                raise ValueError(
                    "base_path and folder_name are required for non-dry-run mode. "
                    "Please provide valid paths or use setup_organization() to configure."
                )
        
        self.base_dir = Path(base_path) / folder_name
        self.history = HistoryManager()
        
        # Pass skip_confirmations to SafetyManager
        if safety_config is None:
            safety_config = {}
        safety_config['skip_confirmations'] = skip_confirmations
        self.safety = SafetyManager(config=safety_config)
        self.session_active = False
        
        # Initialize allowed directories for security validation
        self._initialize_allowed_directories(allowed_dirs)
        
        # Only create directory in non-dry-run mode
        if not dry_run:
            try:
                self.base_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                raise PermissionError(
                    f"Unable to create folder at {self.base_dir}. Please ensure you have "
                    "appropriate permissions or choose a different location."
                )


        # Load categories from config_manager or use simple defaults for backward compatibility
        if config_manager:
            self.config_manager = config_manager
            self.categories = config_manager.get_categories()
        else:
            # Backward compatibility: simple default structure
            from .config_manager import ConfigManager
            self.config_manager = ConfigManager()
            self.categories = self.config_manager.get_categories()

    def _initialize_allowed_directories(self, additional_dirs=None):
        """
        Initialize the list of allowed directories for file operations
        
        Args:
            additional_dirs (list, optional): Additional directories to allow
        """
        # Default allowed directories
        self.allowed_dirs = [
            self.base_dir.resolve(),  # Organization folder
            Path.home().resolve(),    # User home directory
        ]
        
        # Add any additional directories
        if additional_dirs:
            for dir_path in additional_dirs:
                try:
                    resolved_path = Path(dir_path).resolve()
                    if resolved_path.exists() and resolved_path.is_dir():
                        self.allowed_dirs.append(resolved_path)
                except Exception:
                    # Skip invalid paths
                    pass
    
    def _validate_path(self, path, must_exist=True, operation_type="operation"):
        """
        Validate file path for security
        
        Args:
            path (str or Path): Path to validate
            must_exist (bool): Whether the path must exist
            operation_type (str): Type of operation for error messages
            
        Returns:
            Path: Validated absolute path
            
        Raises:
            ValueError: If path is invalid or outside allowed directories
            FileNotFoundError: If path doesn't exist and must_exist is True
            SecurityError: If path appears to be malicious
        """
        try:
            # Convert to Path object and resolve (handles symlinks and ..)
            path = Path(path).resolve()
            
            # Check for system/protected files (starting with .)
            # Note: We no longer make exceptions for .txt or .pdf as those were security holes
            if path.name.startswith('.'):
                raise ValueError(
                    f"Cannot perform {operation_type} on hidden/system files: {path.name}"
                )
            
            # Check if path is within allowed directories
            is_allowed = False
            for allowed_dir in self.allowed_dirs:
                try:
                    # Check if path is relative to allowed directory
                    path.relative_to(allowed_dir)
                    is_allowed = True
                    break
                except ValueError:
                    # Not relative to this allowed directory, continue checking
                    continue
            
            if not is_allowed:
                raise ValueError(
                    f"Path outside allowed directories: {path}\n"
                    f"Allowed directories: {', '.join(str(d) for d in self.allowed_dirs[:2])}"
                )
            
            # FL-008 FIX: Check against sensitive directory blacklist
            # Even if path is within allowed directories, block access to sensitive subdirectories
            path_parts = set(path.parts)
            sensitive_found = path_parts.intersection(self.SENSITIVE_DIRS)
            if sensitive_found:
                raise ValueError(
                    f"Access to sensitive directories is prohibited: {', '.join(sensitive_found)}\n"
                    f"Cannot perform {operation_type} on path: {path}\n"
                    f"This is a security restriction to protect credentials and configuration files."
                )
            
            # Check for Windows system directories
            if os.name == 'nt':
                system_dirs = ['windows', 'program files', 'program files (x86)', 'programdata']
                path_lower = str(path).lower()
                for sys_dir in system_dirs:
                    if f'\\{sys_dir}\\' in path_lower or path_lower.startswith(f'c:\\{sys_dir}'):
                        raise ValueError(
                            f"Cannot perform {operation_type} on system directory: {path}"
                        )
            
            # Check existence if required
            if must_exist and not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            return path
            
        except (OSError, RuntimeError) as e:
            # Handle path resolution errors
            raise ValueError(f"Invalid path for {operation_type}: {path} - {str(e)}")

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
            logger.error(f"Error creating category folders: {e}")
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
            # SECURITY: Validate source path
            source_path = self._validate_path(source_path, must_exist=True, operation_type="copy")

            # Parse the category path
            if '/' in category_path:
                category, subcategory = category_path.split('/')
                dest_dir = self.base_dir / category / subcategory
            else:
                # If no subcategory is specified, use the category as the destination directory
                dest_dir = self.base_dir / category_path
                
            dest_path = dest_dir / source_path.name

            # Handle filename conflicts with content-based duplicate detection
            if dest_path.exists():
                # Check if it's actually a duplicate by comparing file hashes
                finder = DuplicateFinder()
                source_hash = finder.calculate_file_hash(source_path)
                dest_hash = finder.calculate_file_hash(dest_path)
                
                if source_hash and dest_hash and source_hash == dest_hash:
                    # True duplicate - skip copy operation silently
                    if not self.dry_run:
                        self.history.log_operation(
                            str(source_path), 
                            str(dest_path), 
                            operation_type="skip_duplicate_copy",
                            metadata={'reason': 'identical_content'}
                        )
                    return dest_path  # Return existing path
                
                # Different files with same name, rename with counter
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
        except PermissionError as e:
            error_msg = (
                f"Permission denied when copying '{source_path.name}' to '{dest_dir}'.\n\n"
                f"Try running the application as administrator or choose a different destination."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="copy", metadata={'error': error_msg})
            raise PermissionError(error_msg) from e
        except OSError as e:
            # Handle specific OS errors with helpful messages
            if "disk full" in str(e).lower() or "no space" in str(e).lower():
                error_msg = (
                    f"Not enough disk space to copy '{source_path.name}'.\n\n"
                    f"Free up some space or choose a different destination."
                )
            elif "file name too long" in str(e).lower():
                error_msg = (
                    f"File name too long when copying '{source_path.name}'.\n\n"
                    f"Try shortening the file name or choosing a different destination path."
                )
            elif "read-only" in str(e).lower():
                error_msg = (
                    f"Cannot copy to read-only location '{dest_dir}'.\n\n"
                    f"Choose a different destination or remove write protection."
                )
            else:
                error_msg = f"OS error copying '{source_path.name}' to '{dest_dir}': {e}"
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="copy", metadata={'error': error_msg})
            raise OSError(error_msg) from e
        except FileNotFoundError as e:
            error_msg = (
                f"Source file not found: '{source_path}'.\n\n"
                f"The file may have been moved or deleted."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="copy", metadata={'error': error_msg})
            raise FileNotFoundError(error_msg) from e
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = (
                f"Unexpected error copying '{source_path.name}': {type(e).__name__}: {e}\n\n"
                f"Please check file permissions and try again."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="copy", metadata={'error': error_msg})
            raise RuntimeError(error_msg) from e

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
            # SECURITY: Validate source path
            source_path = self._validate_path(source_path, must_exist=True, operation_type="move")
            
            # Parse the category path
            if '/' in category_path:
                category, subcategory = category_path.split('/')
                dest_dir = self.base_dir / category / subcategory
            else:
                # If no subcategory is specified, use the category as the destination directory
                dest_dir = self.base_dir / category_path
                
            dest_path = dest_dir / source_path.name

            # Handle filename conflicts with content-based duplicate detection
            if dest_path.exists():
                # Check if it's actually a duplicate by comparing file hashes
                finder = DuplicateFinder()
                source_hash = finder.calculate_file_hash(source_path)
                dest_hash = finder.calculate_file_hash(dest_path)
                
                if source_hash and dest_hash and source_hash == dest_hash:
                    # True duplicate - ask user if they want to skip
                    if not parent:
                        # No parent widget, skip silently in batch operations
                        return None
                    
                    response = QMessageBox.question(
                        parent,
                        "Duplicate File",
                        f"File '{dest_path.name}' already exists and is identical.\n\nSkip this file?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if response == QMessageBox.StandardButton.Yes:
                        # Log as skipped
                        if not self.dry_run:
                            self.history.log_operation(
                                str(source_path), 
                                str(dest_path), 
                                operation_type="skip_duplicate",
                                metadata={'reason': 'identical_content'}
                            )
                        return None  # Skip the file
                
                # Different files with same name, rename with counter
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
        except PermissionError as e:
            error_msg = (
                f"Permission denied when moving '{source_path.name}' to '{dest_dir}'.\n\n"
                f"Possible causes:\n"
                f"• The file is in use by another program\n"
                f"• You don't have permission to modify the source or destination\n\n"
                f"Try closing programs using this file or running as administrator."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="move", metadata={'error': error_msg})
            raise PermissionError(error_msg) from e
        except OSError as e:
            # Handle specific OS errors with helpful messages
            if "disk full" in str(e).lower() or "no space" in str(e).lower():
                error_msg = (
                    f"Not enough disk space to move '{source_path.name}'.\n\n"
                    f"Free up some space on the destination drive."
                )
            elif "file name too long" in str(e).lower():
                error_msg = (
                    f"File name too long when moving '{source_path.name}'.\n\n"
                    f"Try shortening the file name or choosing a different destination path."
                )
            elif "cross-device" in str(e).lower() or "different" in str(e).lower():
                error_msg = (
                    f"Cannot move '{source_path.name}' across different drives using move operation.\n\n"
                    f"This is a system limitation. The file will be copied instead."
                )
                # Fallback to copy operation for cross-device moves
                try:
                    return self.copy_file(source_path, category_path)
                except Exception as copy_err:
                    error_msg = f"Failed to copy '{source_path.name}' as fallback: {copy_err}"
            else:
                error_msg = f"OS error moving '{source_path.name}' to '{dest_dir}': {e}"
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="move", metadata={'error': error_msg})
            raise OSError(error_msg) from e
        except FileNotFoundError as e:
            error_msg = (
                f"Source file not found: '{source_path}'.\n\n"
                f"The file may have been moved or deleted by another program."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="move", metadata={'error': error_msg})
            raise FileNotFoundError(error_msg) from e
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = (
                f"Unexpected error moving '{source_path.name}': {type(e).__name__}: {e}\n\n"
                f"The file may be locked or in use by another program."
            )
            if not self.dry_run:
                self.history.log_operation(str(source_path), "failed", operation_type="move", metadata={'error': error_msg})
            raise RuntimeError(error_msg) from e

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
            # SECURITY: Validate file path
            file_path = self._validate_path(file_path, must_exist=True, operation_type="rename")

            
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

        except PermissionError as e:
            error_msg = (
                f"Permission denied when renaming '{file_path.name}'.\n\n"
                f"The file may be:\n"
                f"• Open in another program\n"
                f"• Located in a protected directory\n\n"
                f"Close any programs using this file and try again."
            )
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise PermissionError(error_msg) from e
        except FileExistsError as e:
            error_msg = (
                f"Cannot rename '{file_path.name}' to '{new_path.name}' - target file already exists.\n\n"
                f"Choose a different name or enable sequence numbering."
            )
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise FileExistsError(error_msg) from e
        except OSError as e:
            if "file name too long" in str(e).lower():
                error_msg = (
                    f"New file name is too long: '{new_path.name}'.\n\n"
                    f"Try using a shorter name or fewer prefixes/suffixes."
                )
            elif "invalid" in str(e).lower():
                error_msg = (
                    f"Invalid characters in new file name: '{new_path.name}'.\n\n"
                    f"Remove special characters like: \\ / : * ? \" < > |"
                )
            else:
                error_msg = f"OS error renaming '{file_path.name}': {e}"
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise OSError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error renaming '{file_path.name}': {type(e).__name__}: {e}\n\n"
                f"Check that the file exists and is not in use."
            )
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise RuntimeError(error_msg) from e

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
            
        except (PermissionError, FileExistsError, OSError) as e:
            # These exceptions already have detailed messages from rename_file
            error_msg = f"Batch rename failed: {e}"
            self.history.log_operation(
                "batch_rename",
                "failed",
                operation_type="batch_rename",
                metadata={'error': error_msg, 'files': file_paths}
            )
            raise
        except Exception as e:
            error_msg = (
                f"Unexpected error during batch rename: {type(e).__name__}: {e}\n\n"
                f"Files attempted: {len(file_paths)}\n"
                f"Some files may have been renamed successfully before the error occurred."
            )
            self.history.log_operation(
                "batch_rename",
                "failed",
                operation_type="batch_rename",
                metadata={'error': error_msg, 'files': file_paths}
            )
            raise RuntimeError(error_msg) from e

    def categorize_file(self, file_path):
        """
        Categorize a file based on its extension, content, and metadata
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: category/subcategory path
        """
        # SECURITY: Validate file path
        file_path = self._validate_path(file_path, must_exist=True, operation_type="categorize")
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
                # PERFORMANCE FIX: Skip very large files (over 10MB)
                file_size = file_path.stat().st_size
                if file_size > 10 * 1024 * 1024:  # 10MB
                    # Large file, skip content analysis
                    category_path = 'misc/other'
                # SECURITY FIX: Check if file is truly text before reading
                elif not self._is_binary_file(file_path):
                    # PERFORMANCE FIX: Use thread pool with timeout to prevent UI freezes
                    executor = get_io_executor()
                    # Pass timeout to _read_file_sync for internal timeout enforcement
                    # Also keep future.result timeout as defense-in-depth
                    future = executor.submit(_read_file_sync, file_path, 1000, timeout=2.0)
                    
                    try:
                        # Wait max 3 seconds for file read (includes overhead + internal 2s timeout)
                        content = future.result(timeout=3.0)
                        
                        # Check for code patterns
                        if any(pattern in content for pattern in ['def ', 'class ', 'import ', 'function', 'var ', 'const ']):
                            category_path = 'code/other'
                        # Check for data patterns
                        elif any(pattern in content for pattern in ['{', '[', '<html>', '<xml>', 'SELECT ', 'CREATE TABLE']):
                            category_path = 'code/data'
                        # Default to text documents
                        else:
                            category_path = 'documents/text'
                    except concurrent.futures.TimeoutError:
                        # File read timed out (hung handle, slow drive, network issue)
                        print(f"Warning: File read timeout for '{file_path.name}'. Categorizing as misc.")
                        category_path = 'misc/other'
                    except PermissionError as e:
                        # User doesn't have permission to read the file
                        print(f"Warning: Permission denied reading '{file_path.name}' for analysis. Categorizing as misc.")
                        category_path = 'misc/other'
                    except OSError as e:
                        # I/O error, possibly corrupted file or disk issue
                        print(f"Warning: I/O error reading '{file_path.name}': {e}. Categorizing as misc.")
                        category_path = 'misc/other'
                    except UnicodeDecodeError as e:
                        # File not actually text despite extension
                        print(f"Warning: Unable to decode '{file_path.name}' as text. Categorizing as misc.")
                        category_path = 'misc/other'
                    except Exception as e:
                        # Unexpected error during content analysis
                        print(f"Warning: Unexpected error analyzing '{file_path.name}': {type(e).__name__}: {e}. Categorizing as misc.")
                        category_path = 'misc/other'
                else:
                    # Binary file disguised as text extension
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
    
    def _is_binary_file(self, file_path, sample_size=8192):
        """Detect if a file is binary by checking for null bytes and non-text characters
        
        Args:
            file_path: Path to the file to check
            sample_size: Number of bytes to read for detection (default: 8KB)
            
        Returns:
            bool: True if file appears to be binary, False if it appears to be text
        """
        try:
            # Read a sample of the file in binary mode
            with open(file_path, 'rb') as f:
                chunk = f.read(sample_size)
            
            # Empty file is considered text
            if not chunk:
                return False
            
            # Check for null bytes (strong indicator of binary)
            if b'\x00' in chunk:
                return True
            
            # Check for common binary file magic bytes
            binary_signatures = [
                b'\x89PNG',           # PNG
                b'\xFF\xD8\xFF',     # JPEG
                b'GIF87a',           # GIF87a
                b'GIF89a',           # GIF89a
                b'BM',               # BMP
                b'RIFF',             # RIFF (WAV, AVI, etc.)
                b'\x1F\x8B',         # GZIP
                b'PK\x03\x04',       # ZIP
                b'\x7FELF',          # ELF executable
                b'MZ',               # Windows executable
                b'%PDF',             # PDF (actually text-based but often binary content)
            ]
            
            for signature in binary_signatures:
                if chunk.startswith(signature):
                    return True
            
            # Count non-text characters (excluding common control chars like \n, \r, \t)
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7F)) | set(range(0x80, 0x100)))
            non_text_count = sum(1 for byte in chunk if byte not in text_chars)
            
            # If more than 30% non-text characters, consider it binary
            if non_text_count / len(chunk) > 0.3:
                return True
            
            return False
            
        except Exception as e:
            # If we can't determine, assume it's binary to be safe
            print(f"Warning: Could not determine if {file_path.name} is binary: {str(e)}")
            return True

# FileOrganizationApp class and related code removed as it's redundant with the PyQt6 implementation
