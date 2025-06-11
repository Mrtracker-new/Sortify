import os
import sys
import platform
import PyInstaller.__main__
import secrets
from pathlib import Path

def get_platform_config():
    """Get platform-specific configuration"""
    config = {
        'separator': '/',
        'extension': '',
        'icon': 'resources/icons/app_icon.ico',
        'extra_args': []
    }
    
    if platform.system().lower() == 'windows':
        config['separator'] = ';'
        config['extension'] = '.exe'
    elif platform.system().lower() == 'darwin':
        config['icon'] = 'resources/icons/app_icon.icns'
        config['extra_args'] = ['--osx-bundle-identifier', 'com.sortify.app']
    
    return config

def build_application_antivirus_friendly():
    """Build the application using PyInstaller with settings to reduce antivirus false positives"""
    try:
        print("Building application with antivirus-friendly settings...")
        
        # Get platform-specific configuration
        config = get_platform_config()
        
        # Prepare PyInstaller arguments
        app_name = f"Sortify{config['extension']}"
        args = [
            'main.py',
            '--name', app_name,
            '--icon', config['icon'],
            '--windowed',  # No console window
            '--clean',  # Clean PyInstaller cache - important for avoiding false positives
            '--noconfirm',  # Overwrite output directory without asking
            '--noupx',  # Disable UPX compression which often triggers AV
            # Removed encryption key as it's no longer supported in PyInstaller v6.0
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
        ]

        # Add platform-specific arguments
        args.extend(config['extra_args'])
        
        # Run PyInstaller
        PyInstaller.__main__.run(args)
        
        print(f"Application built successfully: {app_name}")
        print("\nNOTE: This build uses antivirus-friendly settings to reduce false positives.")
        print("If you still encounter issues with Windows Defender, please refer to DEFENDER_SOLUTIONS.md")
        return True
    except Exception as e:
        print(f"Error building application: {e}")
        return False

if __name__ == "__main__":
    build_application_antivirus_friendly()