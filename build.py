import PyInstaller.__main__
import platform
import os
from pathlib import Path

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

def build_application():
    """Build the application for current platform"""
    config = get_platform_config()
    
    args = [
        'main.py',
        f'--name=Sortify{config["extension"]}',
        '--onefile',
        '--windowed',
        f'--icon={config["icon"]}',
        '--clean',
        '--noconfirm'
    ]
    
    # Add data files
    data_files = [
        ('ui/styles.css', 'ui'),
        ('resources/icons/*.png', 'resources/icons'),
        ('data', 'data')
    ]
    
    for src, dst in data_files:
        args.append(f'--add-data={src}{config["separator"]}{dst}')
    
    args.extend(config['extra_args'])
    
    print(f"Building for {platform.system()}...")
    try:
        PyInstaller.__main__.run(args)
        print("Build completed successfully!")
    except Exception as e:
        print(f"Error during build: {e}")

if __name__ == "__main__":
    build_application()
