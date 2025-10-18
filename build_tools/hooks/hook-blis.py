# PyInstaller hook for blis
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import os

# Collect all blis files and dependencies
datas, binaries, hiddenimports = collect_all('blis')

# Collect all DLLs from blis
blis_dlls = collect_dynamic_libs('blis')
binaries.extend(blis_dlls)

# Add specific blis modules that might be missing
hiddenimports.extend([
    'blis.py',
    'blis.about',
    'blis.benchmark',
])

# Ensure blis DLLs are included
try:
    import blis
    print(f"Successfully imported blis from {blis.__file__}")
    
    # Get the directory containing blis
    blis_dir = os.path.dirname(blis.__file__)
    print(f"blis directory: {blis_dir}")
    
    # Add any DLL files in this directory
    for file in os.listdir(blis_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
            full_path = os.path.join(blis_dir, file)
            dest_dir = os.path.join('blis')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
            
except ImportError as e:
    print(f"Warning: Could not import blis: {e}")
    print("The built application may have issues with this module.")