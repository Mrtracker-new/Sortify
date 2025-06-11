from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import time
import logging
import os
import threading
from datetime import datetime
from .file_operations import FileOperations
from .categorization import FileCategorizationAI

class FileChangeHandler(FileSystemEventHandler):
    """Enhanced handler for file system events"""
    def __init__(self, file_ops, categorizer):
        self.file_ops = file_ops
        self.categorizer = categorizer
        self.processing_files = set()  # Track files being processed to avoid duplicates
        self.lock = threading.Lock()  # Thread safety for the processing_files set
        self.min_file_age = 1.0  # Minimum file age in seconds before processing
        self.ignored_patterns = ['.tmp', '.crdownload', '.part', '.partial', '.download', '~$']  # Temporary file patterns to ignore
        
    def on_created(self, event):
        """Handle file creation events with improved handling"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            
            # Skip temporary files and partial downloads
            if any(pattern in file_path.name for pattern in self.ignored_patterns):
                logging.debug(f"Ignoring temporary file: {file_path}")
                return
                
            # Process the file in a separate thread to avoid blocking the watcher
            threading.Thread(target=self._process_file, args=(file_path,)).start()
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory and event.dest_path:
            dest_path = Path(event.dest_path)
            
            # Skip temporary files and partial downloads
            if any(pattern in dest_path.name for pattern in self.ignored_patterns):
                logging.debug(f"Ignoring moved temporary file: {dest_path}")
                return
            
            # Skip files that are moved to the destination directory
            # This prevents re-processing files that were just sorted
            if hasattr(self, 'file_ops') and self.file_ops and hasattr(self.file_ops, 'base_dir'):
                if str(dest_path).startswith(str(self.file_ops.base_dir)):
                    logging.debug(f"Ignoring file moved to destination directory: {dest_path}")
                    return
                
            # Process the moved file in a separate thread
            threading.Thread(target=self._process_file, args=(dest_path,)).start()
    
    def _process_file(self, file_path):
        """Process a file for auto-sorting with improved reliability"""
        try:
            # Use a lock to safely check and update the processing_files set
            with self.lock:
                # Skip if already processing this file
                if str(file_path) in self.processing_files:
                    return
                self.processing_files.add(str(file_path))
            
            # Wait for the file to be fully written and stable
            self._wait_for_file_stability(file_path)
            
            # Check if file still exists after waiting
            if not file_path.exists():
                logging.warning(f"File no longer exists, skipping auto-sort: {file_path}")
                return
                
            # Skip zero-byte files
            if file_path.stat().st_size == 0:
                logging.warning(f"Skipping zero-byte file: {file_path}")
                return
            
            # Check if the file is already in a destination directory
            # This prevents re-processing files that were just sorted
            dest_base_dir = self.file_ops.base_dir
            if str(file_path).startswith(str(dest_base_dir)):
                logging.info(f"Skipping file already in destination directory: {file_path}")
                return
                
            logging.info(f"Processing new file: {file_path}")
            
            # Get the appropriate category for the file
            category = self.categorizer.categorize_file(file_path)
            
            # Double-check file still exists before moving
            if file_path.exists():
                # Try to move the file, with retry logic
                self._move_with_retry(file_path, category)
            else:
                logging.warning(f"File disappeared before it could be moved: {file_path}")
                
        except Exception as e:
            logging.error(f"Error auto-sorting file {file_path}: {e}")
        finally:
            # Always remove the file from the processing set when done
            with self.lock:
                self.processing_files.discard(str(file_path))
    
    def _wait_for_file_stability(self, file_path):
        """Wait for a file to be fully written and stable"""
        max_wait_time = 10  # Maximum seconds to wait for file stability
        check_interval = 0.5  # Time between size checks
        
        # First, wait for minimum file age
        try:
            creation_time = os.path.getctime(file_path)
            while (time.time() - creation_time) < self.min_file_age:
                time.sleep(0.1)
        except (FileNotFoundError, OSError):
            return  # File disappeared
        
        # Then check for file size stability
        try:
            last_size = -1
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if not file_path.exists():
                    return  # File disappeared
                    
                current_size = file_path.stat().st_size
                
                if current_size == last_size and current_size > 0:
                    # File size has stabilized
                    time.sleep(0.5)  # Final wait to ensure file is fully written
                    return
                    
                last_size = current_size
                time.sleep(check_interval)
                
        except (FileNotFoundError, OSError):
            return  # File disappeared during checks
    
    def _move_with_retry(self, file_path, category):
        """Try to move a file with retry logic for locked files"""
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                self.file_ops.move_file(file_path, category)
                logging.info(f"Auto-sorted file to {category}: {file_path.name}")
                return True
            except PermissionError:
                # File might be locked by another process
                if attempt < max_retries - 1:
                    logging.warning(f"File locked, retrying in {retry_delay}s: {file_path}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logging.error(f"File locked after {max_retries} attempts: {file_path}")
                    return False
            except Exception as e:
                logging.error(f"Error moving file {file_path}: {e}")
                return False

class FolderWatcher:
    """Enhanced folder watcher with improved reliability and features"""
    def __init__(self, watch_path, file_ops, categorizer):
        self.watch_path = Path(watch_path)
        self.observer = Observer()
        self.handler = FileChangeHandler(file_ops, categorizer)
        self.running = False
        self._observer_was_stopped = False
        self.stats = {
            'started_at': None,
            'files_processed': 0,
            'errors': 0,
            'last_file': None
        }
        
    def start(self):
        """Start watching the folder with improved handling"""
        if not self.running:
            # Create a new observer if it was previously stopped
            if hasattr(self, '_observer_was_stopped') and self._observer_was_stopped:
                self.observer = Observer()
                self._observer_was_stopped = False
            
            # Process existing files in the directory if it's the first start
            if not hasattr(self, '_initial_scan_done') or not self._initial_scan_done:
                threading.Thread(target=self._process_existing_files).start()
                self._initial_scan_done = True
            
            # Start the observer
            self.observer.schedule(self.handler, str(self.watch_path), recursive=True)
            self.observer.start()
            self.running = True
            self.stats['started_at'] = datetime.now()
            logging.info(f"Started watching folder: {self.watch_path}")
            
    def stop(self):
        """Stop watching the folder"""
        if self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            self._observer_was_stopped = True
            logging.info(f"Stopped watching folder: {self.watch_path}")
            
    def is_running(self):
        """Check if watcher is running"""
        return self.running
    
    def get_stats(self):
        """Get statistics about the watcher"""
        return self.stats
    
    def _process_existing_files(self):
        """Process existing files in the watched directory"""
        try:
            logging.info(f"Scanning existing files in {self.watch_path}")
            
            # Get all files in the directory
            files = [f for f in self.watch_path.glob('**/*') if f.is_file()]
            
            if files:
                logging.info(f"Found {len(files)} existing files to process")
                
                # Get destination directory to exclude from processing
                dest_base_dir = None
                if hasattr(self.handler, 'file_ops') and self.handler.file_ops and hasattr(self.handler.file_ops, 'base_dir'):
                    dest_base_dir = str(self.handler.file_ops.base_dir)
                
                # Process each file, skipping those in destination directory
                for file_path in files:
                    # Skip temporary files
                    if any(pattern in file_path.name for pattern in self.handler.ignored_patterns):
                        continue
                    
                    # Skip files in destination directory
                    if dest_base_dir and str(file_path).startswith(dest_base_dir):
                        logging.info(f"Skipping file already in destination directory: {file_path}")
                        continue
                    
                    # Process the file
                    self.handler._process_file(file_path)
                    
                logging.info(f"Completed processing existing files in {self.watch_path}")
            else:
                logging.info(f"No existing files found in {self.watch_path}")
                
        except Exception as e:
            logging.error(f"Error processing existing files: {e}")