import sqlite3
import sqlite3.dbapi2  # Explicitly import to ensure it's included in the build
import os
import sys
import time
import logging
import threading
from pathlib import Path

# Create a logger
logger = logging.getLogger('Sortify.History')

def get_data_dir():
    """Get the data directory path, handling both development and frozen environments"""
    # Check if running as executable
    if getattr(sys, 'frozen', False):
        # When running as executable, use the user's AppData directory
        if sys.platform == 'win32':  # Windows
            app_data = os.path.join(os.environ['APPDATA'], 'Sortify')
            data_dir = Path(app_data) / "data"
        elif sys.platform == 'darwin':  # macOS
            app_data = os.path.expanduser('~/Library/Application Support/Sortify')
            data_dir = Path(app_data) / "data"
        else:  # Linux and others
            app_data = os.path.expanduser('~/.sortify')
            data_dir = Path(app_data) / "data"
    else:
        # In development, use the data directory in the current working directory
        data_dir = Path("data")
    
    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using data directory: {data_dir.absolute()}")
    
    return data_dir

def check_file_permissions(file_path):
    """Check if the file has read/write permissions"""
    try:
        # If file doesn't exist, check if we can write to the directory
        if not file_path.exists():
            dir_path = file_path.parent
            if not dir_path.exists():
                logger.warning(f"Directory does not exist: {dir_path}")
                return False
            
            # Check if we can write to the directory
            try:
                test_file = dir_path / ".permission_test"
                with open(test_file, 'w') as f:
                    f.write("test")
                test_file.unlink()  # Remove the test file
                logger.info(f"Directory is writable: {dir_path}")
                return True
            except Exception as e:
                logger.error(f"Cannot write to directory: {e}")
                return False
        
        # Check if we can open the file in read/write mode
        try:
            # First check if the file is locked by another process
            if os.name == 'nt':  # Windows
                try:
                    # Try to open the file in exclusive mode
                    with open(file_path, 'r+b') as f:
                        # Try to acquire a lock
                        import msvcrt
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        # Release the lock
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    logger.info(f"File is not locked: {file_path}")
                except (IOError, ImportError) as e:
                    logger.warning(f"File may be locked or msvcrt not available: {e}")
                    # Continue anyway, we'll try to open it normally
            
            # Try to open the file in read/write mode
            with open(file_path, 'r+') as f:
                pass
            logger.info(f"File has read/write permissions: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Cannot open file with read/write permissions: {e}")
            return False
    
    except Exception as e:
        logger.error(f"Error checking file permissions: {e}")
        return False

class HistoryManager:
    """Manages the history database for file operations"""
    
    def __init__(self):
        """Initialize the history manager"""
        try:
            # Get the path to the database file
            self.data_dir = get_data_dir()
            self.db_path = self.data_dir / "history.db"
            logger.info(f"Database path: {self.db_path}")
            
            # Check if we have proper permissions
            if not check_file_permissions(self.db_path):
                logger.warning("Database file permission issues detected, attempting to fix")
                self._fix_database_permissions()
            
            # Initialize database connection with retry logic
            self.conn = None
            self.cursor = None
            self._connect_with_retry()
            
            # Create a lock for thread safety
            self.lock = threading.Lock()
            
            logger.info("History manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize history manager: {e}")
            raise
    
    def _connect_with_retry(self, max_retries=3, retry_delay=1.0):
        """Connect to the database with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Connect to the database with a timeout to prevent hanging
                self.conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
                self.cursor = self.conn.cursor()
                
                # Enable foreign keys
                self.cursor.execute("PRAGMA foreign_keys = ON")
                
                # Check database integrity
                self.cursor.execute("PRAGMA integrity_check")
                result = self.cursor.fetchone()[0]
                if result != "ok":
                    logger.warning(f"Database integrity check failed: {result}")
                    raise sqlite3.DatabaseError(f"Database integrity check failed: {result}")
                
                logger.info(f"Connected to database successfully on attempt {attempt+1}")
                return
            except sqlite3.Error as e:
                last_error = e
                logger.warning(f"Database connection attempt {attempt+1} failed: {e}")
                
                # Close any existing connection before retrying
                if self.conn:
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    # Try to fix permissions before retrying
                    self._fix_database_permissions()
                    time.sleep(retry_delay)
        
        # All retries failed
        logger.error(f"Failed to connect to database after {max_retries} attempts: {last_error}")
        raise last_error
    
    def _fix_database_permissions(self):
        """Attempt to fix database file permissions"""
        try:
            logger.info(f"Attempting to fix permissions for {self.db_path}")
            
            # If file exists, try to fix its permissions
            if self.db_path.exists():
                # Remove read-only attribute on Windows
                if os.name == 'nt':
                    try:
                        import stat
                        current_mode = self.db_path.stat().st_mode
                        if current_mode & stat.S_IREAD and not current_mode & stat.S_IWRITE:
                            # File is read-only, remove the read-only attribute
                            os.chmod(str(self.db_path), stat.S_IREAD | stat.S_IWRITE)
                            logger.info(f"Removed read-only attribute from {self.db_path}")
                    except Exception as e:
                        logger.warning(f"Failed to change file mode: {e}")
                    
                    # Try using icacls to set permissions
                    try:
                        import subprocess
                        subprocess.run(['icacls', str(self.db_path), '/grant', 'Everyone:F'], check=False)
                        logger.info("Set permissions using icacls")
                    except Exception as e:
                        logger.warning(f"icacls failed: {e}")
                        
                        # Try using cacls as a fallback
                        try:
                            subprocess.run(['cacls', str(self.db_path), '/e', '/g', 'Everyone:F'], check=False)
                            logger.info("Set permissions using cacls")
                        except Exception as e:
                            logger.warning(f"cacls failed: {e}")
                else:
                    # Unix-like systems
                    try:
                        self.db_path.chmod(0o666)  # Read/write for all users
                        logger.info("Set Unix permissions on database file")
                    except Exception as e:
                        logger.warning(f"Failed to set Unix permissions: {e}")
            
            # Also ensure the directory has proper permissions
            try:
                if os.name == 'nt':
                    import subprocess
                    subprocess.run(['icacls', str(self.data_dir), '/grant', 'Everyone:F'], check=False)
                    logger.info(f"Set directory permissions using icacls on {self.data_dir}")
                else:
                    self.data_dir.chmod(0o777)  # Full permissions for directory
                    logger.info(f"Set Unix permissions on directory {self.data_dir}")
            except Exception as e:
                logger.warning(f"Failed to set directory permissions: {e}")
            
            # Verify the file is now accessible by trying to open it
            try:
                with open(self.db_path, 'a+') as f:
                    pass  # Just testing if we can open it
                logger.info("Verified file is now writable")
                return True
            except Exception as e:
                logger.warning(f"File still not writable after permission fixes: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error fixing database permissions: {e}")
            return False

    def add_history_entry(self, file_name, original_path, new_path, file_size=None, operation_type="move", status="success"):
        """Add an entry to the history table"""
        try:
            with self.lock:
                self.cursor.execute("""
                INSERT INTO history (file_name, original_path, new_path, file_size, operation_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (file_name, original_path, new_path, file_size, operation_type, status))
                self.conn.commit()
                return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Database error in add_history_entry: {e}")
            # Try to reconnect and retry once
            try:
                self._connect_with_retry()
                with self.lock:
                    self.cursor.execute("""
                    INSERT INTO history (file_name, original_path, new_path, file_size, operation_type, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (file_name, original_path, new_path, file_size, operation_type, status))
                    self.conn.commit()
                    return self.cursor.lastrowid
            except sqlite3.Error as retry_error:
                logger.error(f"Database retry error in add_history_entry: {retry_error}")
                return None

    def get_operations(self, limit=100, offset=0):
        """Get recent operations from the database"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, source, target, timestamp FROM operations ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting operations: {str(e)}")
            return []

    def get_history_entries(self, limit=100, offset=0):
        """Get recent history entries from the database"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history entries: {str(e)}")
            return []

    def get_history_by_operation_type(self, operation_type, limit=100, offset=0):
        """Get history entries filtered by operation type"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE operation_type = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (operation_type, limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history by operation type: {str(e)}")
            return []

    def get_history_by_status(self, status, limit=100, offset=0):
        """Get history entries filtered by status"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE status = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (status, limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history by status: {str(e)}")
            return []

    def get_history_by_date_range(self, start_date, end_date, limit=100, offset=0):
        """Get history entries within a date range"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (start_date, end_date, limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history by date range: {str(e)}")
            return []

    def get_history_by_file_name(self, file_name, limit=100, offset=0):
        """Get history entries filtered by file name (partial match)"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE file_name LIKE ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (f"%{file_name}%", limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history by file name: {str(e)}")
            return []

    def get_history_by_path(self, path, limit=100, offset=0):
        """Get history entries filtered by original or new path (partial match)"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE original_path LIKE ? OR new_path LIKE ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (f"%{path}%", f"%{path}%", limit, offset)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting history by path: {str(e)}")
            return []

    def get_operation_count(self):
        """Get the total number of operations"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM operations")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Error getting operation count: {str(e)}")
            return 0

    def get_history_count(self):
        """Get the total number of history entries"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM history")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Error getting history count: {str(e)}")
            return 0

    def delete_operation(self, operation_id):
        """Delete an operation by ID"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM operations WHERE id = ?", (operation_id,))
                return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting operation: {str(e)}")
            return False

    def delete_history_entry(self, entry_id):
        """Delete a history entry by ID"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM history WHERE id = ?", (entry_id,))
                return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting history entry: {str(e)}")
            return False

    def clear_operations(self):
        """Clear all operations from the database"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM operations")
                return True
        except sqlite3.Error as e:
            logging.error(f"Error clearing operations: {str(e)}")
            return False

    def clear_history(self):
        """Clear all history entries from the database"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM history")
                return True
        except Exception as e:
            logging.error(f"Error clearing history: {str(e)}")
            return False

    def __del__(self):
        """Ensure database connection is closed"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def log_operation(self, original_path, new_path, operation_type="move", metadata=None):
        """Log a file operation with metadata"""
        try:
            # Get file information
            file_name = Path(original_path).name
            file_size = Path(original_path).stat().st_size if Path(original_path).exists() else 0

            # Use thread lock for thread safety
            with self.lock:
                cursor = self.conn.cursor()
                
                try:
                    # Use a direct insert without explicit transaction management
                    # since we're using autocommit mode (isolation_level=None)
                    cursor.execute("""
                        INSERT INTO history 
                        (file_name, original_path, new_path, file_size, operation_type) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (file_name, original_path, new_path, file_size, operation_type))
                    return True
                except sqlite3.Error as e:
                    logging.error(f"Database error during log_operation: {str(e)}")
                    return False
        except Exception as e:
            logging.error(f"Error logging operation: {e}")
            return False

    def undo_last_operation(self):
        """Undo the last file operation"""
        try:
            # Use thread lock for thread safety
            with self.lock:
                operations = self.get_operations_with_id(limit=1)
                if not operations:
                    return False, "No operations to undo"
                    
                operation = operations[0]
                source = operation['source']
                target = operation['target']
                op_id = operation['id']
                
                # Check if the file exists at the target location
                if not os.path.exists(target):
                    return False, f"File no longer exists at {target}"
                    
                # Try to move the file back to its original location
                try:
                    # Ensure the directory exists
                    os.makedirs(os.path.dirname(source), exist_ok=True)
                    
                    # Move the file back
                    shutil.move(target, source)
                    
                    # Update the operation status
                    cursor = self.conn.cursor()
                    cursor.execute("""
                        UPDATE history 
                        SET status = 'undone' 
                        WHERE id = ?
                    """, (op_id,))
                    
                    return True, f"Successfully moved {target} back to {source}"
                except Exception as e:
                    return False, f"Error during undo: {e}"
        except Exception as e:
            return False, f"Error retrieving operation: {e}"
            
    def undo_operation_by_id(self, op_id):
        """Undo a specific file operation by ID"""
        try:
            # Use thread lock for thread safety
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT original_path, new_path 
                    FROM history 
                    WHERE id = ? AND status = 'success'
                """, (op_id,))
                result = cursor.fetchone()
                
                if result:
                    original_path, new_path = result
                    if os.path.exists(new_path):
                        try:
                            os.rename(new_path, original_path)
                            cursor.execute("""
                                UPDATE history 
                                SET status = 'undone' 
                                WHERE id = ?
                            """, (op_id,))
                            return True, f"Successfully moved {new_path} back to {original_path}"
                        except Exception as e:
                            return False, f"Error during undo: {e}"
                    return False, "File no longer exists at new location"
                return False, "Operation not found or already undone"
        except Exception as e:
            return False, f"Error during undo: {e}"
            
    def get_operations_with_id(self, limit=10):
        """Get recent operations with their IDs, default last 10"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT id, file_name, original_path, new_path, timestamp FROM history WHERE status = "success" ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            return [{'id': row[0], 'file_name': row[1], 'source': row[2], 'target': row[3], 'timestamp': row[4]} for row in cursor.fetchall()]

    def get_history(self, limit=10):
        """Get recent history entries, default last 10"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT id, file_name, original_path, new_path, timestamp, status FROM history ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            return [{
                'id': row[0], 
                'file_name': row[1], 
                'source': row[2], 
                'target': row[3], 
                'timestamp': row[4],
                'status': row[5]
            } for row in cursor.fetchall()]

    def search_history(self, filename):
        """Search history for a specific filename"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT file_name, original_path, new_path, timestamp, status
                FROM history 
                WHERE file_name LIKE ? 
                ORDER BY timestamp DESC
            """, (f'%{filename}%',))
            return cursor.fetchall()

    def clear_history(self, days_old=30):
        """Clear old history entries"""
        try:
            # Use thread lock for thread safety
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    DELETE FROM history 
                    WHERE datetime(timestamp) < datetime('now', ?)
                """, (f"-{days_old} days",))
                logging.info(f"Cleared history entries older than {days_old} days")
                return True
        except sqlite3.Error as e:
            logging.error(f"Database error during clear_history: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error clearing history: {str(e)}")
            return False
