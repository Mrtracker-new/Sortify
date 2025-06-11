import PyInstaller.__main__
import platform
import os
import sqlite3
import sqlite3.dbapi2
import json
import time
from pathlib import Path

# Ensure these modules are included in the build
import win32security
import ntsecuritycon
import sqlite3
import sqlite3.dbapi2

def get_platform_config():
    """Get platform-specific configuration"""
    system = platform.system().lower()
    
    configs = {
        'darwin': {  # macOS
            'extension': '.app',
            'icon': 'resources/icons/app_icon.icns',
            'separator': ':',
            'extra_args': ['--target-architecture', 'universal2']
        },
        'linux': {
            'extension': '',
            'icon': 'resources/icons/app_icon.png',
            'separator': ':',
            'extra_args': []
        },
        'windows': {
            'extension': '.exe',
            'icon': 'resources/icons/app_icon.ico',
            'separator': ';',
            'extra_args': []
        }
    }
    
    return configs.get(system, configs['windows'])

def initialize_database():
    """Create and initialize the database with required tables"""
    try:
        # Create data directory if it doesn't exist
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # Path to the database file
        db_path = data_dir / "history.db"
        
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
        
        print(f"Database initialized successfully at {db_path}")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def create_default_config():
    """Create a default configuration file in the data directory"""
    try:
        # Create data directory if it doesn't exist
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # Default configuration
        default_config = {
            'last_training_directory': '',
            'last_watch_directory': '',
            'last_schedule_directory': '',
            'last_destination_directory': '',
            'model_path': '',
            'auto_sort_enabled': False,
            'schedule_enabled': False,
            'ai_enabled': False,
            'commands_enabled': False
        }
        
        # Path to the config file
        config_path = data_dir / "config.json"
        
        # Write the default configuration to the file
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        print(f"Default configuration created at {config_path}")
        return True
    except Exception as e:
        print(f"Error creating default configuration: {e}")
        return False

def create_user_data_directories():
    """Create the necessary directories in the user's AppData (or equivalent) folder"""
    try:
        # Determine the appropriate data directory based on the platform
        if platform.system().lower() == 'windows':
            app_data = os.path.join(os.environ['APPDATA'], 'Sortify')
            data_dir = Path(app_data) / "data"
        elif platform.system().lower() == 'darwin':  # macOS
            app_data = os.path.expanduser('~/Library/Application Support/Sortify')
            data_dir = Path(app_data) / "data"
        else:  # Linux and others
            app_data = os.path.expanduser('~/.sortify')
            data_dir = Path(app_data) / "data"
        
        # Create the directories
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test file to verify write permissions
        test_file = data_dir / "test_write.txt"
        try:
            with open(test_file, 'w') as f:
                f.write("Write test")
            # Remove the test file if successful
            test_file.unlink()
            print("Successfully verified write permissions to data directory")
        except Exception as e:
            print(f"Warning: Could not write to data directory: {e}")
        
        print(f"Created user data directories at {data_dir}")
        return data_dir
    except Exception as e:
        print(f"Error creating user data directories: {e}")
        return None

def create_database_in_user_dir(user_data_dir):
    """Create a fresh database directly in the user's data directory"""
    try:
        
        if not user_data_dir:
            print("Cannot create database: User data directory is None")
            return False
            
        # Path to the database file
        db_path = user_data_dir / "history.db"
        
        # If database exists, try to remove it first to ensure a fresh start
        if db_path.exists():
            try:
                # First check if the file is locked by trying to open it
                try:
                    with open(db_path, 'a+') as f:
                        pass  # Just testing if we can open it
                except Exception as lock_error:
                    print(f"Database file appears to be locked: {lock_error}")
                    # Try to close any potential connections
                    try:
                        temp_conn = sqlite3.connect(str(db_path))
                        temp_conn.close()
                    except Exception:
                        pass  # Ignore if we can't connect
                
                # Now try to delete it
                db_path.unlink()
                print(f"Removed existing database at {db_path}")
            except Exception as e:
                print(f"Warning: Could not remove existing database: {e}")
                # Continue anyway, we'll try to create/update it
        
        # Create a new database connection with timeout to prevent hanging
        max_retries = 3
        retry_delay = 1.0  # seconds
        last_error = None
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(str(db_path), timeout=10.0)
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
                
                print(f"Database created successfully at {db_path}")
                return True
            except sqlite3.Error as e:
                last_error = e
                print(f"Database creation attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        
        # All retries failed
        print(f"Failed to create database after {max_retries} attempts: {last_error}")
        return False
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def build_application():
    """Build the application using PyInstaller"""
    try:
        print("Building application...")
        
        # Get platform-specific configuration
        config = get_platform_config()
        
        # Create user data directories and database
        user_data_dir = create_user_data_directories()
        if user_data_dir:
            create_database_in_user_dir(user_data_dir)
        
        # Prepare PyInstaller arguments
        app_name = f"Sortify{config['extension']}"
        args = [
            'main.py',
            '--name', app_name,
            '--icon', config['icon'],
            '--windowed',  # No console window
            '--clean',  # Clean PyInstaller cache
            '--noconfirm',  # Overwrite output directory without asking
            '--add-data', f"ui/styles.css{config['separator']}ui",
            '--add-data', f"resources/icons/*.png{config['separator']}resources/icons",
            '--add-data', f"data{config['separator']}data",
            # Add runtime hook for spaCy
            '--runtime-hook', 'spacy_hook.py',
            # Add hook file for spaCy
            '--additional-hooks-dir', '.',
            # Explicitly include SQLite modules
            '--hidden-import', 'sqlite3',
            '--hidden-import', 'sqlite3.dbapi2',
            # Include other required modules
            '--hidden-import', 'win32security',
            '--hidden-import', 'ntsecuritycon',
            '--hidden-import', 'sklearn.neighbors._partition_nodes',
            '--hidden-import', 'sklearn.utils._cython_blas',
            '--hidden-import', 'sklearn.neighbors._quad_tree',
            '--hidden-import', 'sklearn.tree._utils',
            '--hidden-import', 'spacy.kb',
            '--hidden-import', 'spacy.tokens',
            '--hidden-import', 'spacy.lang.en',
            '--hidden-import', 'en_core_web_sm',
            '--hidden-import', 'en_core_web_sm.load',
            '--hidden-import', 'spacy_legacy',
            '--hidden-import', 'spacy_legacy.architectures',
            '--hidden-import', 'PIL._tkinter_finder',
            '--hidden-import', 'numpy.random.common',
            '--hidden-import', 'numpy.random.bounded_integers',
            '--hidden-import', 'numpy.random.entropy',
            '--hidden-import', 'cymem',
            '--hidden-import', 'cymem.cymem',
            '--hidden-import', 'preshed',
            '--hidden-import', 'preshed.maps',
            '--hidden-import', 'blis',
            '--hidden-import', 'blis.py',
            '--hidden-import', 'thinc',
            '--hidden-import', 'thinc.api',
            # Exclude unnecessary Qt modules to reduce size
            '--exclude-module', 'PyQt5',
            '--exclude-module', 'PyQt5.QtCore',
            '--exclude-module', 'PyQt5.QtGui',
            '--exclude-module', 'PyQt5.QtWidgets',
            '--exclude-module', 'PySide6',
            '--exclude-module', 'PySide6.QtCore',
            '--exclude-module', 'PySide6.QtGui',
            '--exclude-module', 'PySide6.QtWidgets',
            '--exclude-module', 'PySide2',
            '--exclude-module', 'PySide2.QtCore',
            '--exclude-module', 'PySide2.QtGui',
            '--exclude-module', 'PySide2.QtWidgets',
            # Ensure all necessary DLLs are included
            '--collect-all', 'numpy',
            '--collect-all', 'thinc',
            '--collect-all', 'spacy',
            '--collect-all', 'blis',
            '--collect-all', 'cymem',
            '--collect-all', 'preshed',
        ]

        # Add platform-specific arguments
        args.extend(config['extra_args'])
        
        # Run PyInstaller
        PyInstaller.__main__.run(args)
        
        print(f"Application built successfully: {app_name}")
        return True
    except Exception as e:
        print(f"Error building application: {e}")
        return False

def ensure_database_permissions():
    """Ensure the database file has the correct permissions"""
    try:
        # Determine the appropriate data directory based on the platform
        if platform.system().lower() == 'windows':
            app_data = os.path.join(os.environ['APPDATA'], 'Sortify')
            data_dir = Path(app_data) / "data"
        elif platform.system().lower() == 'darwin':  # macOS
            app_data = os.path.expanduser('~/Library/Application Support/Sortify')
            data_dir = Path(app_data) / "data"
        else:  # Linux and others
            app_data = os.path.expanduser('~/.sortify')
            data_dir = Path(app_data) / "data"
        
        # Create the directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure the directory has proper permissions
        try:
            if os.name == 'nt':  # Windows
                # Set directory permissions
                import subprocess
                try:
                    subprocess.run(['icacls', str(data_dir), '/grant', 'Everyone:F'], check=True)
                    print(f"Set directory permissions using icacls on {data_dir}")
                except Exception as dir_perm_error:
                    print(f"Warning: Could not set directory permissions: {dir_perm_error}")
        except Exception as dir_error:
            print(f"Warning: Error setting directory permissions: {dir_error}")
        
        # Check if the database file exists
        db_path = data_dir / "history.db"
        
        # First check if the file is locked or corrupted
        if db_path.exists():
            try:
                # Try to connect to the database to check if it's valid
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                
                if result[0] != 'ok':
                    print(f"Database integrity check failed: {result[0]}")
                    print("Database appears to be corrupted, recreating...")
                    try:
                        db_path.unlink()
                        print(f"Removed corrupted database at {db_path}")
                    except Exception as del_error:
                        print(f"Warning: Could not delete corrupted database: {del_error}")
                        # Try to rename it instead
                        try:
                            backup_path = db_path.with_suffix('.db.bak')
                            db_path.rename(backup_path)
                            print(f"Renamed corrupted database to {backup_path}")
                        except Exception as rename_error:
                            print(f"Warning: Could not rename corrupted database: {rename_error}")
            except Exception as integrity_error:
                print(f"Database may be locked or corrupted: {integrity_error}")
                # Try to recreate the database
                try:
                    db_path.unlink()
                    print(f"Removed potentially corrupted database at {db_path}")
                except Exception as del_error:
                    print(f"Warning: Could not delete database: {del_error}")
                    # Try to rename it instead
                    try:
                        backup_path = db_path.with_suffix('.db.bak')
                        db_path.rename(backup_path)
                        print(f"Renamed database to {backup_path}")
                    except Exception as rename_error:
                        print(f"Warning: Could not rename database: {rename_error}")
        
        # Create a new database if needed
        if not db_path.exists():
            print(f"Database file not found at {db_path}, creating a new one...")
            return create_database_in_user_dir(data_dir)
        
        # Database exists, ensure it has the correct permissions
        try:
            if os.name == 'nt':  # Windows
                # First, ensure the file is not read-only
                import stat
                current_mode = db_path.stat().st_mode
                if current_mode & stat.S_IREAD and not current_mode & stat.S_IWRITE:
                    # File is read-only, remove the read-only attribute
                    os.chmod(str(db_path), stat.S_IREAD | stat.S_IWRITE)
                    print(f"Removed read-only attribute from {db_path}")
                
                # Use icacls to set permissions (most reliable method)
                import subprocess
                # Grant Everyone full control
                try:
                    subprocess.run(['icacls', str(db_path), '/grant', 'Everyone:F'], check=True)
                    print(f"Set permissions using icacls on {db_path}")
                except Exception as icacls_error:
                    print(f"icacls command failed: {icacls_error}")
                    # Try alternative method if icacls fails
                    try:
                        # Try using cacls as a fallback
                        subprocess.run(['cacls', str(db_path), '/e', '/g', 'Everyone:F'], check=True)
                        print(f"Set permissions using cacls on {db_path}")
                    except Exception as cacls_error:
                        print(f"cacls command also failed: {cacls_error}")
                
                # Also try win32security as a backup method
                try:
                    import win32security
                    import ntsecuritycon as con
                    
                    # Get current user's SID
                    username = os.environ.get('USERNAME')
                    domain = os.environ.get('USERDOMAIN')
                    
                    # Set explicit permissions for the current user
                    security = win32security.GetFileSecurity(str(db_path), win32security.DACL_SECURITY_INFORMATION)
                    dacl = security.GetSecurityDescriptorDacl()
                    sid, _, _ = win32security.LookupAccountName(domain, username)
                    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, sid)
                    security.SetSecurityDescriptorDacl(1, dacl, 0)
                    win32security.SetFileSecurity(str(db_path), win32security.DACL_SECURITY_INFORMATION, security)
                    
                    print("Set Windows permissions on database file using win32security")
                except Exception as e:
                    print(f"Win32security method failed: {e}")
                    
                # As a last resort, try to open the file in read/write mode
                try:
                    with open(db_path, 'a+') as f:
                        f.write("")
                    print("Verified file is writable")
                except Exception as e:
                    print(f"Warning: File may still not be writable: {e}")
            else:  # Unix-like
                db_path.chmod(0o666)  # Read/write for all users
                print("Set Unix permissions on database file")
            
            # Verify the database is accessible
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            print(f"Successfully verified database access at {db_path}")
            return True
        except Exception as e:
            print(f"Error setting permissions on database: {e}")
            return False
    except Exception as e:
        print(f"Error ensuring database permissions: {e}")
        return False

if __name__ == "__main__":
    build_application()
    # Ensure database permissions after build
    ensure_database_permissions()
