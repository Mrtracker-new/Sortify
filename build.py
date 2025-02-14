import PyInstaller.__main__
import platform
import os
from pathlib import Path
import shutil
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

def get_platform_config():
    """Get platform-specific configuration"""
    system = platform.system().lower()
    
    configs = {
        'darwin': {  # macOS
            'extension': '.app',
            'icon': 'resources/icons/app_icon.icns',  # macOS icon format
            'separator': ':',
            'extra_args': ['--target-architecture', 'universal2']  # For both Intel and M1
        },
        'linux': {
            'extension': '',  # Linux binary has no extension
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

def build_application():
    """Build the application for current platform"""
    config = get_platform_config()
    
    # Base arguments
    args = [
        'main.py',
        f'--name=Sortify{config["extension"]}',
        '--onefile',
        '--windowed',
        f'--icon={config["icon"]}',
        '--clean',
        '--noconfirm'
    ]
    
    # Add data files with platform-specific separator
    data_files = [
        ('ui/styles.css', 'ui'),
        ('resources/icons/*.png', 'resources/icons'),
        ('data', 'data')
    ]
    
    for src, dst in data_files:
        args.append(f'--add-data={src}{config["separator"]}{dst}')
    
    # Add platform-specific arguments
    args.extend(config['extra_args'])
    
    print(f"Building for {platform.system()}...")
    try:
        PyInstaller.__main__.run(args)
        print("Build completed successfully!")
    except Exception as e:
        print(f"Error during build: {e}")

if __name__ == "__main__":
    build_application()
