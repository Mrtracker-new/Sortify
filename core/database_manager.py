import sqlite3
import threading
import logging
import time
from pathlib import Path
from typing import Any, List, Tuple, Optional, Callable

logger = logging.getLogger('Sortify.DatabaseManager')


class DatabaseManager:
    """Thread-safe database manager with connection pooling"""
    
    def __init__(self, db_path: Path, timeout: float = 10.0):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file
            timeout: Database connection timeout in seconds
        """
        self.db_path = Path(db_path)
        self.timeout = timeout
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Lock for thread-safe operations
        self._lock = threading.Lock()
        
        # Connection tracking for cleanup
        self._connections = {}
        
        logger.info(f"DatabaseManager initialized for: {self.db_path}")
    
    def _get_thread_connection(self) -> sqlite3.Connection:
        """
        Get or create a database connection for the current thread
        
        Returns:
            sqlite3.Connection: Thread-local database connection
        """
        thread_id = threading.get_ident()
        
        # Check if this thread already has a connection
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                # Create a new connection for this thread
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=self.timeout,
                    check_same_thread=True  # Enforce thread safety
                )
                
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Store connection in thread-local storage
                self._local.connection = conn
                
                # Track connection for cleanup
                with self._lock:
                    self._connections[thread_id] = conn
                
                logger.debug(f"Created new database connection for thread {thread_id}")
                
            except sqlite3.Error as e:
                logger.error(f"Failed to create database connection: {e}")
                raise
        
        return self._local.connection
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_mode: str = 'all'
    ) -> Optional[List[Tuple]]:
        """
        Execute a single query with automatic connection management
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            fetch_mode: 'all', 'one', 'none' - how to fetch results
            
        Returns:
            Query results based on fetch_mode, or None for 'none' mode
        """
        conn = self._get_thread_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Handle result fetching based on mode
            if fetch_mode == 'all':
                result = cursor.fetchall()
            elif fetch_mode == 'one':
                result = cursor.fetchone()
            else:  # 'none'
                result = None
            
            # Auto-commit for non-transaction queries
            if not query.strip().upper().startswith('SELECT'):
                conn.commit()
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def execute_transaction(
        self,
        operations: List[Tuple[str, Optional[Tuple]]],
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> bool:
        """
        Execute multiple operations in a single transaction with retry logic
        
        Args:
            operations: List of (query, params) tuples
            max_retries: Number of retry attempts on lock errors
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if transaction succeeded, False otherwise
        """
        conn = self._get_thread_connection()
        
        for attempt in range(max_retries):
            try:
                cursor = conn.cursor()
                
                # Execute all operations in transaction
                for query, params in operations:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                
                # Commit transaction
                conn.commit()
                cursor.close()
                
                logger.debug(f"Transaction completed successfully ({len(operations)} operations)")
                return True
                
            except sqlite3.OperationalError as e:
                # Handle database locked errors with retry
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retry attempt {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Transaction failed: {e}")
                    conn.rollback()
                    return False
                    
            except sqlite3.Error as e:
                logger.error(f"Transaction error: {e}")
                conn.rollback()
                return False
        
        return False
    
    def execute_with_retry(
        self,
        callback: Callable[[sqlite3.Cursor], Any],
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> Optional[Any]:
        """
        Execute a custom callback with cursor and retry logic
        
        Args:
            callback: Function that takes a cursor and performs operations
            max_retries: Number of retry attempts on lock errors
            retry_delay: Delay between retries in seconds
            
        Returns:
            Result from callback function
        """
        conn = self._get_thread_connection()
        
        for attempt in range(max_retries):
            try:
                cursor = conn.cursor()
                result = callback(cursor)
                conn.commit()
                cursor.close()
                return result
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retry attempt {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Operation failed: {e}")
                    conn.rollback()
                    raise
                    
            except sqlite3.Error as e:
                logger.error(f"Operation error: {e}")
                conn.rollback()
                raise
        
        return None
    
    def close_connection(self):
        """Close the connection for the current thread"""
        thread_id = threading.get_ident()
        
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                logger.debug(f"Closed database connection for thread {thread_id}")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._local.connection = None
                
                # Remove from tracking
                with self._lock:
                    self._connections.pop(thread_id, None)
    
    def close_all_connections(self):
        """Close all tracked connections (for cleanup)"""
        with self._lock:
            for thread_id, conn in list(self._connections.items()):
                try:
                    conn.close()
                    logger.debug(f"Closed connection for thread {thread_id}")
                except Exception as e:
                    logger.error(f"Error closing connection for thread {thread_id}: {e}")
            
            self._connections.clear()
        
        # Clear local connection
        if hasattr(self._local, 'connection'):
            self._local.connection = None
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.close_all_connections()
        except Exception as e:
            logger.error(f"Error during DatabaseManager cleanup: {e}")
