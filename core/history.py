import sqlite3
import sqlite3.dbapi2  # Explicitly import to ensure it's included in the build
import os
import sys
import time
import logging
import threading
import shutil
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
    
    # Singleton pattern: Class-level variables
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern with thread-safe double-checked locking"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the history manager"""
        # Prevent re-initialization of singleton instance
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        try:
            # Get the path to the database file
            self.data_dir = get_data_dir()
            self.db_path = self.data_dir / "history.db"
            logger.info(f"Database path: {self.db_path}")
            
            # Check if we have proper permissions
            if not check_file_permissions(self.db_path):
                logger.warning("Database file permission issues detected, attempting to fix")
                self._fix_database_permissions()
            
            # Initialize thread-safe database manager
            from .database_manager import DatabaseManager
            # Use 60-second timeout to handle large batch operations and concurrent access
            # (Previous 10s timeout caused "Database is locked" errors during heavy use)
            self.db_manager = DatabaseManager(self.db_path, timeout=60.0)
            
            # Create a lock for thread safety (for session management, not database)
            self.lock = threading.Lock()
            
            # Session management
            self.current_session_id = None
            self.session_start_time = None
            
            # Run database migration to add session support
            self._migrate_database()
            
            # Mark as initialized
            self._initialized = True
            
            logger.info("History manager initialized successfully (singleton)")
        except Exception as e:
            logger.error(f"Failed to initialize history manager: {e}")
            raise
    
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
    
    def _migrate_database(self):
        """Migrate database to add session support if needed"""
        try:
            # Check if session_id column exists
            columns_result = self.db_manager.execute_query(
                "PRAGMA table_info(history)",
                fetch_mode='all'
            )
            columns = [col[1] for col in columns_result] if columns_result else []
            
            if 'session_id' not in columns:
                logger.info("Adding session_id column to history table")
                self.db_manager.execute_query(
                    "ALTER TABLE history ADD COLUMN session_id TEXT",
                    fetch_mode='none'
                )
                logger.info("Database migration completed successfully")
            else:
                logger.info("Database already has session support")
            
            # Create index on timestamp for faster queries (idempotent with IF NOT EXISTS)
            logger.info("Creating timestamp index if it doesn't exist")
            self.db_manager.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)",
                fetch_mode='none'
            )
            logger.info("Timestamp index ensured")
            
            # Create index on session_id for faster session-based queries
            logger.info("Creating session_id index if it doesn't exist")
            self.db_manager.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_history_session_id ON history(session_id)",
                fetch_mode='none'
            )
            logger.info("Session ID index ensured")
            
            # Create composite index for common query pattern (session + timestamp)
            logger.info("Creating composite session_id+timestamp index if it doesn't exist")
            self.db_manager.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_history_session_timestamp ON history(session_id, timestamp DESC)",
                fetch_mode='none'
            )
            logger.info("Composite session+timestamp index ensured")
            
            # Auto-cleanup old history entries (older than 90 days)
            logger.info("Running automatic cleanup of old history entries")
            try:
                self.clear_old_history(days_old=90)
                logger.info("Automatic cleanup completed")
            except Exception as cleanup_error:
                # Don't fail migration if cleanup fails - just log it
                logger.warning(f"Automatic cleanup failed (non-fatal): {cleanup_error}")
            
        except sqlite3.Error as e:
            logger.error(f"Database migration failed: {e}")
            # Don't raise - old operations can still work without sessions
    
    def start_session(self):
        """Start a new operation session"""
        from datetime import datetime
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start_time = datetime.now()
        logger.info(f"Started new session: {self.current_session_id}")
        return self.current_session_id
    
    def end_session(self):
        """End the current operation session"""
        if self.current_session_id:
            logger.info(f"Ended session: {self.current_session_id}")
            # Optionally create session log file
            self._create_session_log()
            self.current_session_id = None
            self.session_start_time = None
    
    def _create_session_log(self):
        """Create a JSON log file for the current session"""
        if not self.current_session_id:
            return
        
        try:
            import json
            from datetime import datetime
            
            # Get all operations from current session
            operations = self.get_session_operations(self.current_session_id)
            
            if not operations:
                return
            
            # Create log file
            log_file = self.data_dir / f".sortify_session_{self.current_session_id}.json"
            
            log_data = {
                "session_id": self.current_session_id,
                "start_time": self.session_start_time.isoformat() if self.session_start_time else None,
                "end_time": datetime.now().isoformat(),
                "operation_count": len(operations),
                "operations": operations
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"Created session log: {log_file}")
        except Exception as e:
            logger.error(f"Failed to create session log: {e}")
    
    def get_sessions(self, limit=50):
        """Get list of all sessions with metadata"""
        try:
            results = self.db_manager.execute_query(
                """
                SELECT 
                    session_id,
                    COUNT(*) as operation_count,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_ops,
                    SUM(CASE WHEN status = 'undone' THEN 1 ELSE 0 END) as undone_ops
                FROM history 
                WHERE session_id IS NOT NULL
                GROUP BY session_id 
                ORDER BY start_time DESC 
                LIMIT ?
                """,
                params=(limit,),
                fetch_mode='all'
            )
            
            columns = ['session_id', 'operation_count', 'start_time', 'end_time', 'successful_ops', 'undone_ops']
            return [dict(zip(columns, row)) for row in results] if results else []
        except sqlite3.Error as e:
            logger.error(f"Error getting sessions: {e}")
            return []
    
    def get_session_operations(self, session_id):
        """Get all operations for a specific session"""
        try:
            results = self.db_manager.execute_query(
                """
                SELECT 
                    id, file_name, original_path, new_path, 
                    file_size, operation_type, timestamp, status
                FROM history 
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                params=(session_id,),
                fetch_mode='all'
            )
            
            columns = ['id', 'file_name', 'original_path', 'new_path', 
                      'file_size', 'operation_type', 'timestamp', 'status']
            return [dict(zip(columns, row)) for row in results] if results else []
        except sqlite3.Error as e:
            logger.error(f"Error getting session operations: {e}")
            return []
    
    def undo_session(self, session_id):
        """Undo all operations in a session (in reverse order)"""
        try:
            operations = self.get_session_operations(session_id)
            
            if not operations:
                return False, "No operations found in this session"
            
            # Filter only successful operations that haven't been undone
            operations_to_undo = [op for op in operations if op['status'] == 'success']
            
            if not operations_to_undo:
                return False, "No operations to undo in this session"
            
            # Undo in reverse order (last operation first)
            operations_to_undo.reverse()
            
            failed_operations = []
            successful_operations = []
            
            for operation in operations_to_undo:
                success, message = self.undo_operation_by_id(operation['id'])
                if success:
                    successful_operations.append(operation['file_name'])
                else:
                    failed_operations.append((operation['file_name'], message))
            
            # Build result message
            if failed_operations:
                failure_msg = "\n".join([f"  - {name}: {msg}" for name, msg in failed_operations])
                return False, f"Partially undone session. Success: {len(successful_operations)}, Failed: {len(failed_operations)}\nFailures:\n{failure_msg}"
            else:
                return True, f"Successfully undone {len(successful_operations)} operations from session {session_id}"
                
        except Exception as e:
            logger.error(f"Error undoing session: {e}")
            return False, f"Error undoing session: {str(e)}"

    def add_history_entry(self, file_name, original_path, new_path, file_size=None, operation_type="move", status="success"):
        """Add an entry to the history table"""
        try:
            with self.lock:
                session_id = self.current_session_id
            
            # Use transaction for insert and return
            def insert_callback(cursor):
                cursor.execute(
                    "INSERT INTO history (file_name, original_path, new_path, file_size, operation_type, status, session_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (file_name, original_path, new_path, file_size, operation_type, status, session_id)
                )
                return cursor.lastrowid
            
            result = self.db_manager.execute_with_retry(insert_callback)
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error in add_history_entry: {e}")
            return None

    def get_operations(self, limit=100, offset=0):
        """Get recent operations from the database"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, source, target, timestamp FROM operations ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting operations: {str(e)}")
            return []

    def get_history_entries(self, limit=100, offset=0):
        """Get recent history entries from the database"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(limit, offset),
                fetch_mode='all'
            )
            return results if results else []
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
            self.db_manager.execute_query("DELETE FROM operations", fetch_mode='none')
            return True
        except sqlite3.Error as e:
            logging.error(f"Error clearing operations: {str(e)}")
            return False

    def clear_all_history(self):
        """Clear all history entries from the database"""
        try:
            self.db_manager.execute_query("DELETE FROM history", fetch_mode='none')
            return True
        except Exception as e:
            logging.error(f"Error clearing history: {str(e)}")
            return False

    def close(self):
        """Explicitly close the database connection"""
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                # The DatabaseManager handles commit internally
                self.db_manager.close_all_connections()
                logger.info("Database connection closed cleanly")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
    
    def __del__(self):
        """Ensure database connections are closed"""
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close_all_connections()
            except Exception as e:
                logger.error(f"Error closing database connections: {e}")

    def log_operation(self, original_path, new_path, operation_type="move", metadata=None):
        """Log a file operation with metadata"""
        try:
            # Get file information
            file_name = Path(original_path).name
            file_size = Path(original_path).stat().st_size if Path(original_path).exists() else 0

            # Get session_id under lock
            with self.lock:
                session_id = self.current_session_id
            
            # Execute insert query
            success = self.db_manager.execute_transaction([
                (
                    "INSERT INTO history (file_name, original_path, new_path, file_size, operation_type, session_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (file_name, original_path, new_path, file_size, operation_type, session_id)
                )
            ])
            return success
        except Exception as e:
            logging.error(f"Error logging operation: {e}")
            return False

    def undo_last_operation(self):
        """Undo the last file operation"""
        try:
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
                success = self.db_manager.execute_transaction([
                    ("UPDATE history SET status = 'undone' WHERE id = ?", (op_id,))
                ])
                
                if success:
                    return True, f"Successfully moved {os.path.basename(target)} back to {source}"
                else:
                    return False, "Failed to update database"
            except Exception as e:
                return False, f"Error during undo: {e}"
        except Exception as e:
            return False, f"Error retrieving operation: {e}"
            
    def undo_operation_by_id(self, op_id):
        """Undo a specific file operation by ID"""
        try:
            result = self.db_manager.execute_query(
                "SELECT file_name, original_path, new_path FROM history WHERE id = ? AND status = 'success'",
                params=(op_id,),
                fetch_mode='one'
            )
            
            if result:
                file_name, original_path, new_path = result
                
                # Check if file exists at new_path before attempting undo
                if not os.path.exists(new_path):
                    logger.warning(f"Cannot undo operation {op_id}: File not found at {new_path}")
                    return False, (
                        f"Cannot undo: '{file_name}' is missing from {new_path}.\n"
                        f"The file may have been manually moved or deleted.\n"
                        f"Expected location: {new_path}\n"
                        f"Original location: {original_path}\n"
                        f"Please verify the file's current location and restore it manually if needed."
                    )
                
                try:
                    # Ensure original directory exists
                    original_dir = os.path.dirname(original_path)
                    os.makedirs(original_dir, exist_ok=True)
                    
                    # Move file back
                    os.rename(new_path, original_path)
                    
                    # Update database status
                    success = self.db_manager.execute_transaction([
                        ("UPDATE history SET status = 'undone' WHERE id = ?", (op_id,))
                    ])
                    
                    if success:
                        logger.info(f"Successfully undone operation {op_id}: {file_name}")
                        return True, f"Successfully moved {os.path.basename(new_path)} back to {original_path}"
                    else:
                        logger.error(f"Failed to update database after undo for operation {op_id}")
                        return False, "Failed to update database"
                except Exception as e:
                    logger.error(f"Error during undo operation {op_id}: {e}")
                    return False, f"Error during undo: {e}"
                    
            return False, "Operation not found or already undone"
        except Exception as e:
            logger.error(f"Error in undo_operation_by_id: {e}")
            return False, f"Error during undo: {e}"
            
    def get_operations_with_id(self, limit=10):
        """Get recent operations with their IDs, default last 10"""
        results = self.db_manager.execute_query(
            'SELECT id, file_name, original_path, new_path, timestamp FROM history WHERE status = "success" ORDER BY timestamp DESC LIMIT ?',
            params=(limit,),
            fetch_mode='all'
        )
        return [{'id': row[0], 'file_name': row[1], 'source': row[2], 'target': row[3], 'timestamp': row[4]} for row in results] if results else []

    def get_history(self, limit=10):
        """Get recent history entries, default last 10"""
        results = self.db_manager.execute_query(
            'SELECT id, file_name, original_path, new_path, timestamp, status FROM history ORDER BY timestamp DESC LIMIT ?',
            params=(limit,),
            fetch_mode='all'
        )
        return [{
            'id': row[0], 
            'file_name': row[1], 
            'source': row[2], 
            'target': row[3], 
            'timestamp': row[4],
            'status': row[5]
        } for row in results] if results else []

    def search_history(self, filename):
        """Search history for a specific filename"""
        results = self.db_manager.execute_query(
            """
            SELECT file_name, original_path, new_path, timestamp, status
            FROM history 
            WHERE file_name LIKE ? 
            ORDER BY timestamp DESC
            """,
            params=(f'%{filename}%',),
            fetch_mode='all'
        )
        return results if results else []

    def clear_old_history(self, days_old=90):
        """Clear history entries older than specified days (default: 90 days)"""
        try:
            self.db_manager.execute_query(
                """
                DELETE FROM history 
                WHERE datetime(timestamp) < datetime('now', ?)
                """,
                params=(f"-{days_old} days",),
                fetch_mode='none'
            )
            logging.info(f"Cleared history entries older than {days_old} days")
            return True
        except sqlite3.Error as e:
            logging.error(f"Database error during clear_old_history: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error clearing old history: {str(e)}")
            return False
