# PyInstaller hook for cymem
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs  # type: ignore
import os

# Collect all cymem files and dependencies
datas, binaries, hiddenimports = collect_all('cymem')

# Collect all DLLs from cymem
cymem_dlls = collect_dynamic_libs('cymem')
binaries.extend(cymem_dlls)

# Add specific cymem modules that might be missing
hiddenimports.extend([
    'cymem.cymem',
    'cymem.about',
])

# Ensure cymem DLLs are included
try:
    import cymem  # type: ignore
    print(f"Successfully imported cymem from {cymem.__file__}")
    
    # Get the directory containing cymem
    cymem_dir = os.path.dirname(cymem.__file__)
    print(f"cymem directory: {cymem_dir}")
    
    # Add any DLL files in this directory
    for file in os.listdir(cymem_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
            full_path = os.path.join(cymem_dir, file)
            dest_dir = os.path.join('cymem')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
            
except ImportError as e:
    print(f"Warning: Could not import cymem: {e}")
    print("The built application may have issues with this module.")