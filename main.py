import sys
import os
import logging
import sqlite3
import sqlite3.dbapi2  # Explicitly import to ensure it's included in the build
import time
import traceback
import argparse
import atexit
from pathlib import Path

# Windows-specific imports for singleton enforcement
if os.name == 'nt':
    try:
        import win32event
        import win32api
        import winerror
    except ImportError:
        # pywin32 not available - singleton check will be skipped
        win32event = None
        win32api = None
        winerror = None

# ====================================================================
# FIX: PyTorch DLL Loading on Windows
# ====================================================================
# PyTorch requires its DLL directory to be in the search path BEFORE
# PyQt6 is imported. This fixes "c10.dll cannot be loaded" errors.
if os.name == 'nt':  # Windows only
    try:
        import torch
        torch_lib_path = Path(torch.__file__).parent / "lib"
        
        # Add to DLL search path (Python 3.8+)
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(str(torch_lib_path))
            print(f"✓ Added PyTorch DLL directory: {torch_lib_path}")
        else:
            # Fallback for older Python versions
            os.environ['PATH'] = str(torch_lib_path) + os.pathsep + os.environ.get('PATH', '')
            print(f"✓ Added PyTorch to PATH: {torch_lib_path}")
            
    except ImportError:
        print("⚠ PyTorch not found - AI features will be unavailable")
    except Exception as e:
        print(f"⚠ Warning: Could not configure PyTorch DLL path: {e}")
# ====================================================================

# Note: spaCy model loading has been moved to background thread in main_window.py
# to prevent UI blocking during startup. The ModelLoaderThread will handle
# spaCy path configuration and model loading asynchronously.

# Now import the rest of the modules
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, Qt

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

# Global mutex handle for singleton enforcement
_app_mutex = None

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

def log_corruption_details(db_path, integrity_result):
    """Log detailed information about database corruption"""
    logger.error("="*60)
    logger.error("DATABASE CORRUPTION DETECTED")
    logger.error("="*60)
    logger.error(f"Database path: {db_path}")
    logger.error(f"Integrity check result: {integrity_result}")
    logger.error(f"Database size: {db_path.stat().st_size if db_path.exists() else 'N/A'} bytes")
    logger.error("="*60)

def attempt_database_repair(db_path):
    """Attempt to repair corrupted database using REINDEX and VACUUM
    
    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info("Attempting database repair...")
    
    try:
        # First, try REINDEX to rebuild indexes
        logger.info("Stage 1: Attempting REINDEX...")
        try:
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("REINDEX")
            conn.commit()
            conn.close()
            logger.info("✓ REINDEX completed successfully")
            
            # Check if integrity is fixed
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result == "ok":
                logger.info("✓ Database repaired successfully with REINDEX!")
                return True, "Database repaired successfully with REINDEX"
            else:
                logger.warning(f"REINDEX completed but integrity still failing: {result}")
        except Exception as e:
            logger.warning(f"REINDEX failed: {e}")
        
        # Second, try VACUUM to rebuild the database file
        logger.info("Stage 2: Attempting VACUUM...")
        try:
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
            conn.close()
            logger.info("✓ VACUUM completed successfully")
            
            # Check if integrity is fixed
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result == "ok":
                logger.info("✓ Database repaired successfully with VACUUM!")
                return True, "Database repaired successfully with VACUUM"
            else:
                logger.warning(f"VACUUM completed but integrity still failing: {result}")
        except Exception as e:
            logger.warning(f"VACUUM failed: {e}")
        
        # If both repairs failed
        logger.error("All repair attempts failed")
        return False, "All repair attempts (REINDEX, VACUUM) failed"
        
    except Exception as e:
        logger.error(f"Critical error during repair attempt: {e}")
        return False, f"Critical error during repair: {e}"

def offer_database_recovery(db_path, backup_path):
    """Offer user options for database recovery when repairs fail
    
    Returns:
        str: User's choice - 'create_new', 'exit', or None if GUI unavailable
    """
    logger.info("Offering database recovery options to user...")
    
    # Check if we're in GUI mode
    if QApplication.instance():
        # GUI mode - show dialog
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Database Corruption Detected")
        msg.setText(
            "The application database is corrupted and cannot be repaired automatically.\n\n"
            f"A backup has been created at:\n{backup_path}\n\n"
            "What would you like to do?"
        )
        msg.setInformativeText(
            "Option 1: Create a new database (you will lose all history)\n"
            "Option 2: Exit and seek help (backup is preserved for manual recovery)"
        )
        
        create_btn = msg.addButton("Create New Database", QMessageBox.ButtonRole.DestructiveRole)
        exit_btn = msg.addButton("Exit Application", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(exit_btn)
        
        msg.exec()
        
        if msg.clickedButton() == create_btn:
            logger.warning("User chose to create new database (data will be lost)")
            return 'create_new'
        else:
            logger.info("User chose to exit and preserve backup")
            return 'exit'
    else:
        # CLI mode or no GUI available - print to console
        print("\n" + "="*60)
        print("DATABASE CORRUPTION DETECTED")
        print("="*60)
        print(f"The database is corrupted and cannot be repaired automatically.")
        print(f"A backup has been created at: {backup_path}")
        print("\nOptions:")
        print("  1. Create new database (lose all history)")
        print("  2. Exit application (preserve backup for manual recovery)")
        print("="*60)
        
        try:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == '1':
                logger.warning("User chose to create new database (data will be lost)")
                return 'create_new'
            else:
                logger.info("User chose to exit and preserve backup")
                return 'exit'
        except (EOFError, KeyboardInterrupt):
            logger.info("User interrupted - exiting")
            return 'exit'

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
                # Log detailed corruption information
                log_corruption_details(db_path, result)
                
                # STAGE 1: Attempt repairs (REINDEX, VACUUM)
                logger.info("Stage 1: Attempting non-destructive repairs...")
                repair_success, repair_message = attempt_database_repair(db_path)
                
                if repair_success:
                    logger.info(f"✓ Database repaired successfully: {repair_message}")
                    logger.info("Application will continue with repaired database")
                else:
                    logger.error(f"✗ Repair failed: {repair_message}")
                    
                    # STAGE 2: Create timestamped backup (preserve existing .db.bak)
                    logger.info("Stage 2: Creating timestamped backup...")
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = db_path.parent / f"history.db.backup_{timestamp}"
                    
                    try:
                        # Copy corrupted database to backup (don't use rename to preserve original)
                        import shutil
                        shutil.copy2(db_path, backup_path)
                        logger.info(f"✓ Created backup at: {backup_path}")
                        
                        # Also preserve as .db.bak if it doesn't exist (for compatibility)
                        legacy_backup = db_path.with_suffix(".db.bak")
                        if not legacy_backup.exists():
                            shutil.copy2(db_path, legacy_backup)
                            logger.info(f"✓ Created legacy backup at: {legacy_backup}")
                        else:
                            logger.info(f"Preserving existing backup at: {legacy_backup}")
                            
                    except Exception as backup_error:
                        logger.error(f"Failed to create backup: {backup_error}")
                        backup_path = db_path.with_suffix(".db.bak")  # Fallback path for user message
                    
                    # STAGE 3: Offer user recovery options
                    logger.info("Stage 3: Requesting user decision...")
                    user_choice = offer_database_recovery(db_path, backup_path)
                    
                    if user_choice == 'create_new':
                        # STAGE 4: User chose to recreate database (data loss accepted)
                        logger.warning("Stage 4: Recreating database per user request")
                        logger.warning(f"User accepted data loss. Backup preserved at: {backup_path}")
                        
                        try:
                            db_path.unlink()
                            logger.info("Deleted corrupted database")
                            create_new_database(db_path)
                            logger.info(f"Created new database. Old data preserved at: {backup_path}")
                        except Exception as e:
                            logger.error(f"Failed to recreate database: {e}")
                            # Try one more time without deletion
                            try:
                                create_new_database(db_path)
                            except Exception as final_error:
                                logger.critical(f"Fatal: Cannot create database: {final_error}")
                    else:
                        # User chose to exit - preserve backup and exit gracefully
                        logger.info("User chose to exit. Backup preserved for manual recovery.")
                        logger.info(f"Backup location: {backup_path}")
                        return False
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
        
        # Create index on timestamp for faster queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)
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

def check_single_instance():
    """Check if another instance is already running using Windows mutex
    
    Returns:
        bool: True if this is the only instance, False if another is running
    """
    global _app_mutex
    
    # Only enforce singleton on Windows with pywin32 available
    if os.name != 'nt' or win32event is None:
        logger.info("Singleton check skipped (not Windows or pywin32 unavailable)")
        return True
    
    mutex_name = "Global\\Sortify_SingleInstance_Mutex"
    
    try:
        # Try to create a named mutex
        _app_mutex = win32event.CreateMutex(None, False, mutex_name)
        last_error = win32api.GetLastError()
        
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            # Another instance is already running
            logger.warning("Another instance of Sortify is already running")
            return False
        
        # Successfully acquired mutex - we're the only instance
        logger.info("Application mutex acquired successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to create mutex: {e}")
        # If mutex creation fails, allow the app to run to avoid blocking users
        return True

def release_mutex():
    """Release the application mutex on exit"""
    global _app_mutex
    
    if _app_mutex and os.name == 'nt' and win32api is not None:
        try:
            win32api.CloseHandle(_app_mutex)
            logger.info("Application mutex released")
        except Exception as e:
            logger.error(f"Failed to release mutex: {e}")

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Sortify - Intelligent File Organization System',
        epilog='Examples:\n'
               '  python main.py --dry-run --source "C:\\Downloads" --organize\n'
               '  python main.py --yes --source "C:\\Downloads" --organize\n'
               '  python main.py  (launches GUI)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without moving files')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompts')
    parser.add_argument('--source', type=str,
                       help='Source directory to organize')
    parser.add_argument('--organize', action='store_true',
                       help='Organize files in the source directory')
    parser.add_argument('--dest', type=str,
                       help='Destination base path (default: ~/Documents)')
    parser.add_argument('--folder', type=str, default='Organized Files',
                       help='Organization folder name (default: Organized Files)')
    
    return parser.parse_args()

def run_cli_mode(args):
    """
    Run Sortify in CLI mode (headless, no GUI)
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        from core.file_operations import FileOperations
        
        print("\n" + "="*60)
        print("🗂️  Sortify - File Organization")
        print("="*60)
        
        # Validate source directory
        if not args.source:
            print("\n❌ Error: --source argument is required for CLI mode")
            print("   Example: python main.py --dry-run --source \"C:\\Downloads\" --organize")
            return 1
        
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"\n❌ Error: Source directory does not exist: {source_path}")
            return 1
        
        if not source_path.is_dir():
            print(f"\n❌ Error: Source path is not a directory: {source_path}")
            return 1
        
        # Determine destination
        dest_base = args.dest or str(Path.home() / "Documents")
        
        print(f"\n📂 Source: {source_path}")
        print(f"📁 Destination: {dest_base}/{args.folder}")
        
        if args.dry_run:
            print("🔍 Mode: DRY-RUN (preview only)")
        elif args.yes:
            print("⚡ Mode: AUTO (no confirmations)")
        else:
            print("👤 Mode: INTERACTIVE")
        
        print()
        
        # Initialize FileOperations
        file_ops = FileOperations(
            base_path=dest_base,
            folder_name=args.folder, 
            dry_run=args.dry_run,
            skip_confirmations=args.yes
        )
        
        # Create category folders (skipped in dry-run mode)
        if not args.dry_run:
            file_ops.create_category_folders()
        
        # Get all files from source directory
        files = [f for f in source_path.iterdir() if f.is_file()]
        
        if not files:
            print("ℹ️  No files found in source directory.")
            return 0
        
        print(f"📊 Found {len(files)} files to process\n")
        
        # Start operation session
        file_ops.start_operations()
        
        # Process each file
        processed = 0
        skipped = 0
        errors = 0
        
        for file_path in files:
            try:
                # Categorize the file
                category_path = file_ops.categorize_file(file_path)
                
                # Move the file (or record dry-run operation)
                result = file_ops.move_file(file_path, category_path, skip_confirmation=args.yes)
                
                if result:
                    processed += 1
                    if not args.dry_run:
                        print(f"  ✓ {file_path.name} → {category_path}")
                else:
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                print(f"  ✗ {file_path.name}: {str(e)}")
        
        # Finalize operations
        file_ops.finalize_operations()
        
        # Print results
        print("\n" + "="*60)
        
        if args.dry_run:
            # Show dry-run table
            if hasattr(file_ops, 'dry_run_manager') and file_ops.dry_run_manager:
                file_ops.dry_run_manager.print_operations_table()
                file_ops.dry_run_manager.print_summary()
        else:
            # Show actual results
            print("\n✨ Organization Complete!")
            print(f"   Processed: {processed} files")
            if skipped > 0:
                print(f"   Skipped: {skipped} files")
            if errors > 0:
                print(f"   Errors: {errors} files")
            print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"CLI mode error: {e}", exc_info=True)
        return 1

def main():
    # Parse command-line arguments
    args = parse_arguments()
    
    # Check if we should run in CLI mode (headless, no GUI)
    if args.dry_run or args.source:
        # Run in CLI mode
        return run_cli_mode(args)
    
    # Check for single instance (GUI mode only) BEFORE creating QApplication
    if not check_single_instance():
        # Another instance is already running - show error and exit
        # Create minimal QApplication just for the error dialog
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Sortify Already Running",
            "Another instance of Sortify is already running.\n\n"
            "Please use the existing window or close it before starting a new instance.\n\n"
            "This restriction prevents database conflicts."
        )
        logger.warning("Exiting: Another instance is already running")
        return 1
    
    # Register mutex cleanup handler
    atexit.register(release_mutex)
    
    # Otherwise, run in GUI mode (original behavior)
    # Initialize application
    app = QApplication(sys.argv)
    
    # Global reference to history_manager for cleanup
    history_manager = None
    
    # Define cleanup function
    def cleanup():
        """Clean up resources before exit"""
        try:
            if history_manager:
                history_manager.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Set application name and organization
    app.setApplicationName("Sortify")
    app.setOrganizationName("RNR")
    
    # Log application start
    logger.info("Application starting")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"SQLite version: {sqlite3.sqlite_version}")
    logger.info(f"Running from: {get_base_path()}")
    
    # Splash Screen
    from PyQt6.QtGui import QPixmap, QColor
    from PyQt6.QtWidgets import QSplashScreen
    
    splash_base = get_base_path() / 'resources' / 'icons' / 'rnr.png'
    if not splash_base.exists():
        # Fallback if png not found, try ico or just no splash
        splash_base = get_base_path() / 'resources' / 'icons' / 'app_icon.ico'
        
    splash = None
    if splash_base.exists():
        # Create splash
        pixmap = QPixmap(str(splash_base))
        # Optional: Resize if too big
        if pixmap.width() > 600:
             pixmap = pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
             
        splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        splash.showMessage("Starting Sortify...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("white"))
        app.processEvents()
    
    # helper to apply theme - Apply EARLY for splash to look right if we styled it (we didn't yet, but good practice)
    try:
        from ui.theme_manager import ThemeManager
        theme_manager = ThemeManager()
        app.setStyleSheet(theme_manager.get_stylesheet())
    except Exception as e:
        logger.error(f"Failed to apply theme: {e}")
    
    if splash:
        splash.showMessage("Verifying database...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("white"))
        app.processEvents()
        
    # Ensure database file exists and is accessible
    if not ensure_database_file():
        logger.critical("Failed to ensure database file, exiting application")
        sys.exit(1)
    
    if splash:
        splash.showMessage("Loading interface...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("white"))
        app.processEvents()

    # Import UI modules here to avoid circular imports
    from ui.main_window import MainWindow
    from core.history import HistoryManager
    
    # Initialize history manager with retry logic
    max_retries = 3
    retry_delay = 1.0
    # history_manager already declared as nonlocal in cleanup
    
    for attempt in range(max_retries):
        try:
            history_manager = HistoryManager()
            logger.info("History manager initialized successfully")
            break
        except Exception as e:
            logger.error(f"Failed to initialize history manager (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                if splash:
                     splash.showMessage(f"Retrying database connection ({attempt+1})...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("yellow"))
                     app.processEvents()
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                # Show error message to user
                error_msg = (
                    "Failed to initialize the application database. "
                    "Please ensure no other instance of the application is running "
                    "and you have write permissions to the data directory."
                )
                if splash: splash.close()
                QMessageBox.critical(None, "Database Error", error_msg)
                logger.critical("Failed to initialize history manager after all attempts, exiting application")
                sys.exit(1)
    
    if splash:
        splash.showMessage("Readying UI...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, QColor("white"))
        app.processEvents()
        
    # Create and show main window
    main_window = MainWindow(history_manager)
    main_window.show()
    
    if splash:
        splash.finish(main_window)
    
    # Start the application event loop
    exit_code = app.exec()
    
    # Log application exit
    logger.info(f"Application exiting with code {exit_code}")
    
    # Return exit code
    return exit_code

if __name__ == "__main__":
    sys.exit(main())