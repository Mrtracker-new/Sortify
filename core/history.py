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

# Configuration constants for history retention
MAX_HISTORY_DAYS = 90  # Keep history for last 90 days
MAX_HISTORY_RECORDS = 10000  # Maximum number of history records to retain
CLEANUP_ON_STARTUP = True  # Enable automatic cleanup on startup
DATABASE_SIZE_WARNING_MB = 100  # Warn if database exceeds this size in MB

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
            
            # Auto-cleanup old history entries if enabled
            if CLEANUP_ON_STARTUP:
                logger.info("Running automatic history cleanup on startup")
                try:
                    # Get initial database stats
                    initial_stats = self.get_database_stats()
                    logger.info(
                        f"Database stats before cleanup: "
                        f"{initial_stats.get('total_records', 0)} records, "
                        f"{initial_stats.get('database_size_mb', 0):.2f} MB"
                    )
                    
                    # Run comprehensive cleanup
                    cleanup_stats = self.cleanup_history(
                        days_old=MAX_HISTORY_DAYS,
                        max_records=MAX_HISTORY_RECORDS
                    )
                    
                    if cleanup_stats.get('total_deleted', 0) > 0:
                        logger.info(
                            f"Cleanup removed {cleanup_stats['total_deleted']} records, "
                            f"saved {cleanup_stats.get('space_saved_mb', 0):.2f} MB"
                        )
                    
                    # Check database health
                    is_healthy, warnings = self.check_database_health()
                    if not is_healthy:
                        for warning in warnings:
                            logger.warning(f"Database health: {warning}")
                    
                except Exception as cleanup_error:
                    # Don't fail migration if cleanup fails - just log it
                    logger.warning(f"Automatic cleanup failed (non-fatal): {cleanup_error}")
            else:
                logger.info("Automatic cleanup on startup is disabled (CLEANUP_ON_STARTUP=False)")
            
            
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
    
    def _validate_undo_operation(self, op_id):
        """Validate that an operation can be undone
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT file_name, original_path, new_path FROM history WHERE id = ? AND status = 'success'",
                params=(op_id,),
                fetch_mode='one'
            )
            
            if not result:
                return False, f"Operation {op_id} not found or already undone"
            
            file_name, original_path, new_path = result
            
            # Check if file exists at current location (new_path)
            if not os.path.exists(new_path):
                return False, f"File '{file_name}' not found at {new_path}. It may have been moved or deleted."
            
            # Check if original directory exists or can be created
            original_dir = os.path.dirname(original_path)
            if original_dir and not os.path.exists(original_dir):
                # Check if we can create the directory
                try:
                    # Try to check parent directory permissions
                    parent_dir = os.path.dirname(original_dir)
                    if parent_dir and not os.access(parent_dir, os.W_OK):
                        return False, f"Cannot create directory {original_dir}: parent directory not writable"
                except Exception as e:
                    return False, f"Cannot validate directory creation for {original_dir}: {e}"
            
            # Check if destination path would conflict with existing file
            if os.path.exists(original_path):
                return False, f"Cannot undo: a file already exists at {original_path}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating undo operation {op_id}: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _redo_operation_by_id(self, op_id):
        """Redo an operation (reverse an undo) - used for rollback
        
        Moves file from original_path back to new_path and updates status back to 'success'
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT file_name, original_path, new_path FROM history WHERE id = ? AND status = 'undone'",
                params=(op_id,),
                fetch_mode='one'
            )
            
            if not result:
                return False, "Operation not found or not in undone state"
            
            file_name, original_path, new_path = result
            
            # Check if file exists at original location
            if not os.path.exists(original_path):
                logger.error(f"Redo failed: File not found at {original_path}")
                return False, f"File not found at {original_path}"
            
            try:
                # Ensure new directory exists
                new_dir = os.path.dirname(new_path)
                if new_dir:
                    os.makedirs(new_dir, exist_ok=True)
                
                # Move file back to new_path
                os.rename(original_path, new_path)
                
                # Update database status back to success
                success = self.db_manager.execute_transaction([
                    ("UPDATE history SET status = 'success' WHERE id = ?", (op_id,))
                ])
                
                if success:
                    logger.info(f"Successfully redone operation {op_id}: {file_name}")
                    return True, f"Redone operation for {file_name}"
                else:
                    logger.error(f"Failed to update database after redo for operation {op_id}")
                    return False, "Failed to update database"
                    
            except Exception as e:
                logger.error(f"Error during redo operation {op_id}: {e}")
                return False, f"Error during redo: {e}"
                
        except Exception as e:
            logger.error(f"Error in _redo_operation_by_id: {e}")
            return False, f"Error during redo: {e}"
    
    def undo_session(self, session_id):
        """Undo all operations in a session (in reverse order) - TRANSACTIONAL
        
        Uses two-phase commit:
        1. Validation phase: Check all operations can be undone
        2. Execution phase: Perform undos with rollback on failure
        
        If any operation fails, all successfully undone operations are rolled back
        to maintain filesystem consistency.
        """
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
            
            # PHASE 1: VALIDATION - Check all operations can be undone
            logger.info(f"Phase 1: Validating {len(operations_to_undo)} operations for session {session_id}")
            validation_errors = []
            
            for operation in operations_to_undo:
                is_valid, error_msg = self._validate_undo_operation(operation['id'])
                if not is_valid:
                    validation_errors.append((operation['file_name'], error_msg))
            
            # If validation failed, don't proceed with undo
            if validation_errors:
                logger.warning(f"Session undo validation failed for {len(validation_errors)} operations")
                error_details = "\n".join([f"  - {name}: {msg}" for name, msg in validation_errors])
                return False, (
                    f"Cannot undo session: {len(validation_errors)} operation(s) failed validation.\n"
                    f"No changes were made to maintain consistency.\n\n"
                    f"Validation errors:\n{error_details}\n\n"
                    f"Please resolve these issues before attempting to undo this session."
                )
            
            # PHASE 2: EXECUTION - All validations passed, perform actual undo
            logger.info(f"Phase 2: Executing undo for {len(operations_to_undo)} operations")
            successfully_undone = []  # Track for potential rollback
            
            for operation in operations_to_undo:
                success, message = self.undo_operation_by_id(operation['id'])
                
                if success:
                    successfully_undone.append(operation)
                    logger.debug(f"Undone operation {operation['id']}: {operation['file_name']}")
                else:
                    # ROLLBACK: An undo failed, restore all previously undone operations
                    logger.error(f"Undo failed for operation {operation['id']}: {message}")
                    logger.warning(f"Rolling back {len(successfully_undone)} successfully undone operations")
                    
                    rollback_failures = []
                    for undone_op in reversed(successfully_undone):  # Reverse again to restore in correct order
                        redo_success, redo_message = self._redo_operation_by_id(undone_op['id'])
                        if not redo_success:
                            rollback_failures.append((undone_op['file_name'], redo_message))
                    
                    # Build comprehensive error message
                    error_msg = (
                        f"Session undo failed at operation: {operation['file_name']}\n"
                        f"Error: {message}\n\n"
                    )
                    
                    if rollback_failures:
                        # Critical: rollback failed, filesystem is in inconsistent state
                        logger.critical(f"CRITICAL: Rollback failed for {len(rollback_failures)} operations!")
                        rollback_errors = "\n".join([f"  - {name}: {msg}" for name, msg in rollback_failures])
                        error_msg += (
                            f"CRITICAL: Rollback failed for {len(rollback_failures)} operation(s).\n"
                            f"The filesystem may be in an inconsistent state.\n\n"
                            f"Rollback failures:\n{rollback_errors}\n\n"
                            f"Please manually verify file locations and restore consistency."
                        )
                    else:
                        # Rollback succeeded, filesystem is consistent
                        logger.info(f"Successfully rolled back {len(successfully_undone)} operations")
                        error_msg += (
                            f"Successfully rolled back {len(successfully_undone)} operation(s).\n"
                            f"All files have been restored to their previous state.\n"
                            f"No changes were made to the filesystem."
                        )
                    
                    return False, error_msg
            
            # All operations succeeded
            logger.info(f"Successfully undone {len(successfully_undone)} operations from session {session_id}")
            return True, f"Successfully undone {len(successfully_undone)} operations from session {session_id}"
                
        except Exception as e:
            logger.error(f"Unexpected error undoing session: {e}")
            return False, f"Unexpected error undoing session: {str(e)}"

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
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE operation_type = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(operation_type, limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting history by operation type: {str(e)}")
            return []

    def get_history_by_status(self, status, limit=100, offset=0):
        """Get history entries filtered by status"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE status = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(status, limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting history by status: {str(e)}")
            return []

    def get_history_by_date_range(self, start_date, end_date, limit=100, offset=0):
        """Get history entries within a date range"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(start_date, end_date, limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting history by date range: {str(e)}")
            return []

    def get_history_by_file_name(self, file_name, limit=100, offset=0):
        """Get history entries filtered by file name (partial match)"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE file_name LIKE ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(f"%{file_name}%", limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting history by file name: {str(e)}")
            return []

    def get_history_by_path(self, path, limit=100, offset=0):
        """Get history entries filtered by original or new path (partial match)"""
        try:
            results = self.db_manager.execute_query(
                "SELECT id, file_name, original_path, new_path, file_size, operation_type, timestamp, status FROM history WHERE original_path LIKE ? OR new_path LIKE ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params=(f"%{path}%", f"%{path}%", limit, offset),
                fetch_mode='all'
            )
            return results if results else []
        except sqlite3.Error as e:
            logging.error(f"Error getting history by path: {str(e)}")
            return []

    def get_operation_count(self):
        """Get the total number of operations"""
        try:
            result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM operations",
                fetch_mode='one'
            )
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Error getting operation count: {str(e)}")
            return 0

    def get_history_count(self):
        """Get the total number of history entries"""
        try:
            result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM history",
                fetch_mode='one'
            )
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Error getting history count: {str(e)}")
            return 0

    def delete_operation(self, operation_id):
        """Delete an operation by ID"""
        try:
            self.db_manager.execute_query(
                "DELETE FROM operations WHERE id = ?",
                params=(operation_id,),
                fetch_mode='none'
            )
            return True
        except sqlite3.Error as e:
            logging.error(f"Error deleting operation: {str(e)}")
            return False

    def delete_history_entry(self, entry_id):
        """Delete a history entry by ID"""
        try:
            self.db_manager.execute_query(
                "DELETE FROM history WHERE id = ?",
                params=(entry_id,),
                fetch_mode='none'
            )
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
        """Clear history entries older than specified days (default: 90 days)
        
        Args:
            days_old: Number of days to retain (entries older than this are deleted)
            
        Returns:
            int: Number of records deleted, or -1 on error
        """
        try:
            # Count records before deletion for logging
            count_result = self.db_manager.execute_query(
                """
                SELECT COUNT(*) FROM history 
                WHERE datetime(timestamp) < datetime('now', ?)
                """,
                params=(f"-{days_old} days",),
                fetch_mode='one'
            )
            count_to_delete = count_result[0] if count_result else 0
            
            if count_to_delete == 0:
                logger.info(f"No history entries older than {days_old} days to delete")
                return 0
            
            # Delete old records
            self.db_manager.execute_query(
                """
                DELETE FROM history 
                WHERE datetime(timestamp) < datetime('now', ?)
                """,
                params=(f"-{days_old} days",),
                fetch_mode='none'
            )
            
            # Vacuum database to reclaim space
            try:
                self.db_manager.execute_query("VACUUM", fetch_mode='none')
                logger.info("Database vacuumed to reclaim space")
            except Exception as vacuum_error:
                logger.warning(f"Failed to vacuum database: {vacuum_error}")
            
            logger.info(f"Cleared {count_to_delete} history entries older than {days_old} days")
            return count_to_delete
        except sqlite3.Error as e:
            logger.error(f"Database error during clear_old_history: {str(e)}")
            return -1
        except Exception as e:
            logger.error(f"Error clearing old history: {str(e)}")
            return -1
    
    def enforce_max_history_size(self, max_records=MAX_HISTORY_RECORDS):
        """Enforce maximum number of history records by deleting oldest entries
        
        Args:
            max_records: Maximum number of records to retain
            
        Returns:
            int: Number of records deleted, or -1 on error
        """
        try:
            # Count total records
            count_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM history",
                fetch_mode='one'
            )
            total_records = count_result[0] if count_result else 0
            
            if total_records <= max_records:
                logger.info(f"History size ({total_records} records) within limit ({max_records})")
                return 0
            
            records_to_delete = total_records - max_records
            
            # Delete oldest records, preserving active sessions
            # First, try to delete from completed sessions only
            self.db_manager.execute_query(
                """
                DELETE FROM history 
                WHERE id IN (
                    SELECT id FROM history 
                    WHERE status IN ('success', 'undone')
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
                """,
                params=(records_to_delete,),
                fetch_mode='none'
            )
            
            # Vacuum database to reclaim space
            try:
                self.db_manager.execute_query("VACUUM", fetch_mode='none')
                logger.info("Database vacuumed to reclaim space")
            except Exception as vacuum_error:
                logger.warning(f"Failed to vacuum database: {vacuum_error}")
            
            logger.info(f"Deleted {records_to_delete} oldest records to enforce limit of {max_records}")
            return records_to_delete
        except sqlite3.Error as e:
            logger.error(f"Database error during enforce_max_history_size: {str(e)}")
            return -1
        except Exception as e:
            logger.error(f"Error enforcing max history size: {str(e)}")
            return -1
    
    def cleanup_history(self, days_old=MAX_HISTORY_DAYS, max_records=MAX_HISTORY_RECORDS):
        """Comprehensive history cleanup using both time-based and count-based policies
        
        Applies both retention policies and uses whichever is more restrictive.
        
        Args:
            days_old: Maximum age of records to keep
            max_records: Maximum number of records to keep
            
        Returns:
            dict: Statistics about cleanup operation
        """
        try:
            logger.info(f"Starting history cleanup (max_age={days_old} days, max_records={max_records})")
            
            # Get stats before cleanup
            stats_before = self.get_database_stats()
            
            # Apply time-based cleanup
            time_deleted = self.clear_old_history(days_old=days_old)
            
            # Apply count-based cleanup
            count_deleted = self.enforce_max_history_size(max_records=max_records)
            
            # Get stats after cleanup
            stats_after = self.get_database_stats()
            
            cleanup_stats = {
                'time_based_deleted': time_deleted if time_deleted >= 0 else 0,
                'count_based_deleted': count_deleted if count_deleted >= 0 else 0,
                'total_deleted': (time_deleted if time_deleted >= 0 else 0) + (count_deleted if count_deleted >= 0 else 0),
                'records_before': stats_before.get('total_records', 0),
                'records_after': stats_after.get('total_records', 0),
                'size_before_mb': stats_before.get('database_size_mb', 0),
                'size_after_mb': stats_after.get('database_size_mb', 0),
                'space_saved_mb': stats_before.get('database_size_mb', 0) - stats_after.get('database_size_mb', 0)
            }
            
            logger.info(
                f"Cleanup complete: deleted {cleanup_stats['total_deleted']} records, "
                f"saved {cleanup_stats['space_saved_mb']:.2f} MB "
                f"({cleanup_stats['records_before']} -> {cleanup_stats['records_after']} records)"
            )
            
            return cleanup_stats
        except Exception as e:
            logger.error(f"Error during cleanup_history: {e}")
            return {
                'error': str(e),
                'total_deleted': 0,
                'time_based_deleted': 0,
                'count_based_deleted': 0
            }
    
    def get_database_stats(self):
        """Get database statistics including size, record count, and age range
        
        Returns:
            dict: Database statistics
        """
        try:
            stats = {}
            
            # Get database file size
            if self.db_path.exists():
                db_size_bytes = self.db_path.stat().st_size
                stats['database_size_bytes'] = db_size_bytes
                stats['database_size_mb'] = db_size_bytes / (1024 * 1024)
            else:
                stats['database_size_bytes'] = 0
                stats['database_size_mb'] = 0
            
            # Get total record count
            count_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM history",
                fetch_mode='one'
            )
            stats['total_records'] = count_result[0] if count_result else 0
            
            # Get oldest and newest timestamps
            time_range = self.db_manager.execute_query(
                "SELECT MIN(timestamp), MAX(timestamp) FROM history",
                fetch_mode='one'
            )
            if time_range and time_range[0]:
                stats['oldest_record'] = time_range[0]
                stats['newest_record'] = time_range[1]
                
                # Calculate age span
                from datetime import datetime
                try:
                    oldest = datetime.fromisoformat(time_range[0])
                    newest = datetime.fromisoformat(time_range[1])
                    age_span = (newest - oldest).days
                    stats['age_span_days'] = age_span
                    
                    # Calculate average records per day
                    if age_span > 0:
                        stats['avg_records_per_day'] = stats['total_records'] / age_span
                    else:
                        stats['avg_records_per_day'] = stats['total_records']
                except Exception as date_error:
                    logger.warning(f"Error calculating date statistics: {date_error}")
            else:
                stats['oldest_record'] = None
                stats['newest_record'] = None
                stats['age_span_days'] = 0
                stats['avg_records_per_day'] = 0
            
            # Get status breakdown
            status_counts = self.db_manager.execute_query(
                "SELECT status, COUNT(*) FROM history GROUP BY status",
                fetch_mode='all'
            )
            stats['status_breakdown'] = {row[0]: row[1] for row in status_counts} if status_counts else {}
            
            return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}
    
    def check_database_health(self):
        """Check database health and warn if issues detected
        
        Returns:
            tuple: (is_healthy: bool, warnings: list of str)
        """
        try:
            warnings = []
            stats = self.get_database_stats()
            
            # Check database size
            db_size_mb = stats.get('database_size_mb', 0)
            if db_size_mb > DATABASE_SIZE_WARNING_MB:
                warnings.append(
                    f"Database size ({db_size_mb:.2f} MB) exceeds recommended limit ({DATABASE_SIZE_WARNING_MB} MB). "
                    f"Consider reducing MAX_HISTORY_DAYS or MAX_HISTORY_RECORDS."
                )
            
            # Check record count
            total_records = stats.get('total_records', 0)
            if total_records > MAX_HISTORY_RECORDS * 1.5:
                warnings.append(
                    f"Record count ({total_records}) significantly exceeds limit ({MAX_HISTORY_RECORDS}). "
                    f"Automatic cleanup may not be working properly."
                )
            
            # Check growth rate
            avg_per_day = stats.get('avg_records_per_day', 0)
            if avg_per_day > 500:
                warnings.append(
                    f"High growth rate detected ({avg_per_day:.1f} records/day). "
                    f"Database may fill quickly. Consider more frequent cleanup or lower retention."
                )
            
            is_healthy = len(warnings) == 0
            
            if warnings:
                logger.warning(f"Database health check found {len(warnings)} issue(s)")
                for warning in warnings:
                    logger.warning(f"  - {warning}")
            else:
                logger.info("Database health check passed")
            
            return is_healthy, warnings
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            return False, [f"Health check failed: {str(e)}"]
