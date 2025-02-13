import PyInstaller.__main__
import shutil
from pathlib import Path
import os
import time
import sqlite3

def clean_directory(path):
    """Safely clean a directory with retries"""
    if not Path(path).exists():
        return

    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            # Try to close any open database connections
            if path == 'dist' and Path('dist/data/history.db').exists():
                try:
                    conn = sqlite3.connect('dist/data/history.db')
                    conn.close()
                except:
                    pass

            # Wait a moment to ensure connections are closed
            time.sleep(1)
            
            # Remove the directory
            shutil.rmtree(path)
            print(f"Successfully cleaned {path}")
            break
        except PermissionError as e:
            if attempt == max_attempts - 1:
                print(f"Warning: Could not remove {path}: {e}")
                # If it's the last attempt, try to remove files individually
                try:
                    for root, dirs, files in os.walk(path, topdown=False):
                        for name in files:
                            try:
                                os.unlink(os.path.join(root, name))
                            except:
                                pass
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                            except:
                                pass
                except:
                    pass
            else:
                print(f"Attempt {attempt + 1}: Waiting for files to be released...")
                time.sleep(2)  # Wait longer between attempts

def clean_spec_files():
    """Remove all spec files"""
    for spec in Path().glob('*.spec'):
        try:
            spec.unlink()
        except Exception as e:
            print(f"Warning: Could not remove spec file {spec}: {e}")

print("Starting build process...")

# Clean up old builds
print("Cleaning old builds...")
clean_directory('build')
clean_directory('dist')

# Remove old spec files
print("Cleaning spec files...")
clean_spec_files()

print("Configuring PyInstaller...")
try:
    PyInstaller.__main__.run([
        'main.py',
        '--name=FileOrganizer',
        '--onefile',
        '--windowed',
        '--icon=resources/icons/app_icon.ico',
        '--add-data=ui/styles.css;ui',
        '--add-data=resources/icons/*.png;resources/icons',
        '--add-data=data;data',
        '--clean',
        '--noconfirm'
    ])
    print("Build completed successfully!")
except Exception as e:
    print(f"Error during build: {e}")