import sqlite3
from pathlib import Path
import os
from datetime import datetime
import time
import logging

class HistoryManager:
    def __init__(self):
        self.db_path = Path('data/history.db')
        
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        
        max_attempts = 3
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            try:
                self.conn = sqlite3.connect(str(self.db_path))
                self.init_db()
                break
            except (sqlite3.OperationalError, PermissionError) as e:
                last_error = e
                attempt += 1
                if attempt == max_attempts:
                    raise PermissionError(f"Could not access database after {max_attempts} attempts: {str(last_error)}")
                time.sleep(0.5)

    def init_db(self):
        """Initialize the database tables"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_operation(self, source, target):
        """Add a new file operation to history"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO operations (source, target) VALUES (?, ?)',
                (str(source), str(target))
            )
            self.conn.commit()
            logging.info(f"Added operation to history: {source} -> {target}")
        except sqlite3.Error as e:
            logging.error(f"Database error: {str(e)}")
            raise

    def get_operations(self, limit=10):
        """Get recent operations, default last 10"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT source, target FROM operations ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        )
        return [{'source': row[0], 'target': row[1]} for row in cursor.fetchall()]

    def get_last_operation(self):
        """Get the most recent operation"""
        operations = self.get_operations(limit=1)
        return operations[0] if operations else None

    def remove_last_operation(self):
        """Remove the most recent operation from history"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'DELETE FROM operations WHERE id = (SELECT id FROM operations ORDER BY timestamp DESC LIMIT 1)'
            )
            self.conn.commit()
            logging.info("Removed last operation from history")
        except sqlite3.Error as e:
            logging.error(f"Database error: {str(e)}")
            raise

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

            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO history 
                (file_name, original_path, new_path, file_size, operation_type) 
                VALUES (?, ?, ?, ?, ?)
            """, (file_name, original_path, new_path, file_size, operation_type))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error logging operation: {e}")
            return False

    def undo_last_operation(self):
        """Undo the last file operation"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, original_path, new_path 
                FROM history 
                WHERE status = 'success'
                ORDER BY timestamp DESC LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                op_id, original_path, new_path = result
                if os.path.exists(new_path):
                    os.rename(new_path, original_path)
                    cursor.execute("""
                        UPDATE history 
                        SET status = 'undone' 
                        WHERE id = ?
                    """, (op_id,))
                    self.conn.commit()
                    return True, f"Successfully moved {new_path} back to {original_path}"
                return False, "File no longer exists at new location"
            return False, "No operations to undo"
        except Exception as e:
            return False, f"Error during undo: {e}"

    def get_history(self, limit=10):
        """Get recent file operations"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_name, original_path, new_path, timestamp, status
            FROM history 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()

    def search_history(self, filename):
        """Search for specific file in history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_name, original_path, new_path, timestamp, status
            FROM history 
            WHERE file_name LIKE ?
            ORDER BY timestamp DESC
        """, (f"%{filename}%",))
        return cursor.fetchall()

    def clear_history(self, days_old=30):
        """Clear old history entries"""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM history 
            WHERE datetime(timestamp) < datetime('now', ?)
        """, (f"-{days_old} days",))
        self.conn.commit()
