# PyInstaller hook for en_core_web_sm
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

try:
    import en_core_web_sm
    # Get the path to the model
    model_path = en_core_web_sm.__path__[0]
    
    # Add all files from the model directory
    datas = [(model_path, 'en_core_web_sm')]
    
    # Add hidden imports for the model
    hiddenimports = [
        'en_core_web_sm',
        'en_core_web_sm.load',
    ]
    
    print(f"Successfully added en_core_web_sm model from {model_path}")
except ImportError:
    print("Warning: en_core_web_sm model not found. It will not be included in the package.")
    datas = []
    hiddenimports = []