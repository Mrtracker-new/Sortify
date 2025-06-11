# PyInstaller hook for preshed
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import os

# Collect all preshed files and dependencies
datas, binaries, hiddenimports = collect_all('preshed')

# Collect all DLLs from preshed
preshed_dlls = collect_dynamic_libs('preshed')
binaries.extend(preshed_dlls)

# Add specific preshed modules that might be missing
hiddenimports.extend([
    'preshed.maps',
    'preshed.counter',
    'preshed.about',
])

# Ensure preshed DLLs are included
try:
    import preshed
    print(f"Successfully imported preshed from {preshed.__file__}")
    
    # Get the directory containing preshed
    preshed_dir = os.path.dirname(preshed.__file__)
    print(f"preshed directory: {preshed_dir}")
    
    # Add any DLL files in this directory
    for file in os.listdir(preshed_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
            full_path = os.path.join(preshed_dir, file)
            dest_dir = os.path.join('preshed')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
            
except ImportError as e:
    print(f"Warning: Could not import preshed: {e}")
    print("The built application may have issues with this module.")