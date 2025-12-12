import sys
import os
import logging
import sqlite3
import sqlite3.dbapi2  # Explicitly import to ensure it's included in the build
import time
import traceback
from pathlib import Path

# Set up spaCy model path before importing any modules that use spaCy
try:
    import spacy
    import spacy.util
    
    # When running from PyInstaller bundle, set up model paths
    if getattr(sys, '_MEIPASS', None):
        possible_model_paths = [
            os.path.join(sys._MEIPASS, 'en_core_web_sm'),
            os.path.join(os.path.dirname(sys.executable), 'en_core_web_sm'),
        ]
        
        for model_path in possible_model_paths:
            if os.path.exists(model_path):
                print(f"Setting spaCy model path to: {model_path}")
                spacy.util.set_data_path(model_path)
                break
    
    # Test if model can be loaded
    try:
        import en_core_web_sm
        print(f"✓ spaCy model found at: {en_core_web_sm.__path__[0]}")
    except ImportError:
        print("⚠ Warning: spaCy model 'en_core_web_sm' not found.")
        print("  The application will start but AI features will be limited.")
        print("  To install the model, run: python -m spacy download en_core_web_sm")
        
except Exception as e:
    print(f"⚠ Warning: Error initializing spaCy: {e}")
    print("  The application will continue with basic file categorization.")

# Now import the rest of the modules
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

# Set up logging
log_file = Path(os.path.expanduser('~')) / 'AppData' / 'Roaming' / 'Sortify' / 'debug.log'
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(log_file),
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='a'
)

# Add console handler for development environment
if not getattr(sys, 'frozen', False):
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

# Create a logger
logger = logging.getLogger('Sortify')

# Log uncaught exceptions
def exception_hook(exctype, value, tb):
    logger.critical(f"Uncaught exception: {exctype.__name__}, {value}")
    logger.critical("Traceback:")
    for line in traceback.format_tb(tb):
        logger.critical(line.strip())
    
    # Show error message to user
    if QApplication.instance():
        error_msg = f"An unexpected error occurred: {value}\n\nPlease check the log file for details: {log_file}"
        QMessageBox.critical(None, "Critical Error", error_msg)
    
    # Call the original exception hook
    sys.__excepthook__(exctype, value, tb)

# Set the exception hook
sys.excepthook = exception_hook

# Determine base path
def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running in development environment
        return Path(__file__).parent

# Determine data directory
def get_data_dir():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use user's AppData folder
        data_dir = Path(os.path.expanduser('~')) / 'AppData' / 'Roaming' / 'Sortify' / 'data'
    else:
        # Running in development environment - use local data folder
        data_dir = get_base_path() / 'data'
    
    # Ensure the directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Data directory: {data_dir}")
    return data_dir

# Verify database connection with retry logic
def verify_database_connection(db_path, max_retries=3, retry_delay=1.0):
    """Verify database connection with retry logic"""
    logger.info(f"Verifying database connection to {db_path}")
    
    for attempt in range(max_retries):
        try:
            # Try to connect with a timeout to prevent hanging
            conn = sqlite3.connect(str(db_path), timeout=10.0)
            cursor = conn.cursor()
            
            # Run a simple query to verify connection
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Close connection
            conn.close()
            
            logger.info(f"Database connection verified successfully on attempt {attempt+1}")
            return True
        except sqlite3.Error as e:
            logger.warning(f"Database connection attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    logger.error(f"Failed to verify database connection after {max_retries} attempts")
    return False

# Ensure database file exists
def ensure_database_file():
    data_dir = get_data_dir()
    db_path = data_dir / "history.db"
    
    logger.info(f"Checking database file at {db_path}")
    
    # Set directory permissions on Windows
    if os.name == 'nt':
        try:
            import subprocess
            subprocess.run(['icacls', str(data_dir), '/grant', 'Everyone:F'], check=False)
            logger.info("Set directory permissions using icacls")
        except Exception as e:
            logger.warning(f"Failed to set directory permissions: {e}")
    
    # Check if database file exists
    if not db_path.exists():
        logger.info("Database file does not exist, creating new one")
        create_new_database(db_path)
    else:
        logger.info("Database file exists, checking integrity")
        # Check database integrity
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result != "ok":
                logger.warning(f"Database integrity check failed: {result}")
                # Backup and recreate database
                backup_path = db_path.with_suffix(".db.bak")
                try:
                    if backup_path.exists():
                        backup_path.unlink()
                    db_path.rename(backup_path)
                    logger.info(f"Renamed corrupted database to {backup_path}")
                    create_new_database(db_path)
                except Exception as e:
                    logger.error(f"Failed to backup and recreate database: {e}")
                    # Try to delete and recreate
                    try:
                        db_path.unlink()
                        logger.info("Deleted corrupted database")
                        create_new_database(db_path)
                    except Exception as del_error:
                        logger.error(f"Failed to delete corrupted database: {del_error}")
            else:
                logger.info("Database integrity check passed")
        except Exception as e:
            logger.warning(f"Failed to check database integrity: {e}")
            # Try to verify if the database is accessible
            if not verify_database_connection(db_path):
                logger.warning("Database is not accessible, attempting to fix permissions")
                attempt_fix_database_permissions(db_path)
    
    # Set file permissions
    set_database_permissions(db_path)
    
    # Final verification
    if not verify_database_connection(db_path):
        logger.error("Database is still not accessible after all attempts")
        # Show error message to user
        if QApplication.instance():
            error_msg = (
                "Cannot access the database file. "
                "Please ensure no other instance of the application is running "
                "and you have write permissions to the data directory."
            )
            QMessageBox.critical(None, "Database Error", error_msg)
        return False
    
    return True

def create_new_database(db_path):
    """Create a new database file with the required schema"""
    try:
        import sqlite3
        # Create a new database connection
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create operations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            original_path TEXT NOT NULL,
            new_path TEXT NOT NULL,
            file_size INTEGER,
            operation_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success'
        )
        """)
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logging.info("Created new database file successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to create new database: {str(e)}")
        return False

def _set_windows_file_permissions(db_path):
    """Helper function to set Windows file permissions using multiple methods"""
    import stat
    import subprocess
    
    # Remove read-only attribute
    try:
        current_mode = db_path.stat().st_mode
        if current_mode & stat.S_IREAD and not current_mode & stat.S_IWRITE:
            os.chmod(str(db_path), stat.S_IREAD | stat.S_IWRITE)
            logging.info(f"Removed read-only attribute from {db_path}")
    except Exception as mode_error:
        logging.warning(f"Could not check/set file mode: {str(mode_error)}")
    
    # Try icacls first
    try:
        subprocess.run(['icacls', str(db_path), '/grant', 'Everyone:F'], check=False)
        logging.info(f"Set permissions using icacls on {db_path}")
        return True
    except Exception as icacls_error:
        logging.warning(f"Failed to set permissions with icacls: {str(icacls_error)}")
    
    # Try cacls as fallback
    try:
        subprocess.run(['cacls', str(db_path), '/e', '/g', 'Everyone:F'], check=False)
        logging.info(f"Set permissions using cacls on {db_path}")
        return True
    except Exception as cacls_error:
        logging.warning(f"Failed to set permissions with cacls: {str(cacls_error)}")
    
    # Try win32security as last resort
    try:
        import win32security
        import ntsecuritycon as con
        
        username = os.environ.get('USERNAME')
        domain = os.environ.get('USERDOMAIN')
        
        security = win32security.GetFileSecurity(str(db_path), win32security.DACL_SECURITY_INFORMATION)
        dacl = security.GetSecurityDescriptorDacl()
        sid, _, _ = win32security.LookupAccountName(domain, username)
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, sid)
        security.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(str(db_path), win32security.DACL_SECURITY_INFORMATION, security)
        
        logging.info("Set Windows permissions using win32security")
        return True
    except ImportError:
        logging.warning("win32security not available")
    except Exception as win32_error:
        logging.warning(f"Failed to set permissions with win32security: {str(win32_error)}")
    
    return False

def set_database_permissions(db_path):
    """Set appropriate permissions on the database file"""
    try:
        if os.name == 'nt':  # Windows
            success = _set_windows_file_permissions(db_path)
            
            # Verify file is writable
            try:
                with open(db_path, 'a+') as f:
                    f.write("")
                logging.info("Verified file is writable")
            except Exception as write_error:
                logging.warning(f"File may still not be writable: {str(write_error)}")
            
            return success
        else:  # Unix-like
            import stat
            db_path.chmod(0o666)  # Read/write for all users
            logging.info("Set Unix permissions on database file")
            return True
    except Exception as e:
        logging.error(f"Failed to set permissions: {str(e)}")
        return False

def attempt_fix_database_permissions(db_path):
    """Attempt to fix database file permissions"""
    try:
        logger.info(f"Attempting to fix permissions for {db_path}")
        
        if db_path.exists():
            # Use the consolidated permission setting function
            set_database_permissions(db_path)
        
        # Verify if the file is accessible
        return verify_database_connection(db_path)
    except Exception as e:
        logger.error(f"Failed to fix database permissions: {e}")
        return False

def main():
    # Initialize application
    app = QApplication(sys.argv)
    
    # Set application name and organization
    app.setApplicationName("Sortify")
    app.setOrganizationName("RNR")
    
    # Log application start
    logger.info("Application starting")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"SQLite version: {sqlite3.sqlite_version}")
    logger.info(f"Running from: {get_base_path()}")
    
    # Ensure database file exists and is accessible
    if not ensure_database_file():
        logger.critical("Failed to ensure database file, exiting application")
        sys.exit(1)
    
    # Import UI modules here to avoid circular imports
    from ui.main_window import MainWindow
    from core.history import HistoryManager
    
    # Initialize history manager with retry logic
    max_retries = 3
    retry_delay = 1.0
    history_manager = None
    
    for attempt in range(max_retries):
        try:
            history_manager = HistoryManager()
            logger.info("History manager initialized successfully")
            break
        except Exception as e:
            logger.error(f"Failed to initialize history manager (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                # Show error message to user
                error_msg = (
                    "Failed to initialize the application database. "
                    "Please ensure no other instance of the application is running "
                    "and you have write permissions to the data directory."
                )
                QMessageBox.critical(None, "Database Error", error_msg)
                logger.critical("Failed to initialize history manager after all attempts, exiting application")
                sys.exit(1)
    
    # Create and show main window
    main_window = MainWindow(history_manager)
    main_window.show()
    
    # Start the application event loop
    exit_code = app.exec()
    
    # Log application exit
    logger.info(f"Application exiting with code {exit_code}")
    
    # Return exit code
    return exit_code

if __name__ == "__main__":
    sys.exit(main())