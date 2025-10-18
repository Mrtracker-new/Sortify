# PyInstaller hook for thinc
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_submodules  # type: ignore
import os
import sys

# Collect all thinc files and dependencies
datas, binaries, hiddenimports = collect_all('thinc')

# Collect all DLLs from thinc
thinc_dlls = collect_dynamic_libs('thinc')
binaries.extend(thinc_dlls)

# Add all thinc submodules
hiddenimports.extend(collect_submodules('thinc'))

# Add specific thinc modules that might be missing
hiddenimports.extend([
    'thinc.api',
    'thinc.backends',
    'thinc.backends.numpy_ops',
    'thinc.backends.cupy_ops',
    'thinc.backends.ops',
    'thinc.layers',
    'thinc.loss',
    'thinc.model',
    'thinc.optimizers',
    'thinc.schedules',
    'thinc.shims',
    'thinc.types',
    'thinc.util',
])

# Ensure numpy_ops is included
try:
    import thinc.backends.numpy_ops  # type: ignore
    print(f"Successfully imported thinc.backends.numpy_ops from {thinc.backends.numpy_ops.__file__}")
    
    # Get the directory containing numpy_ops
    numpy_ops_dir = os.path.dirname(thinc.backends.numpy_ops.__file__)
    print(f"numpy_ops directory: {numpy_ops_dir}")
    
    # Add any DLL files in this directory
    for file in os.listdir(numpy_ops_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
            full_path = os.path.join(numpy_ops_dir, file)
            dest_dir = os.path.join('thinc', 'backends')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
            
    # Also add the parent directory DLLs
    parent_dir = os.path.dirname(numpy_ops_dir)
    for file in os.listdir(parent_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib'):
            full_path = os.path.join(parent_dir, file)
            dest_dir = os.path.join('thinc')
            binaries.append((full_path, dest_dir))
            print(f"Added binary from parent dir: {full_path} -> {dest_dir}")
            
except ImportError as e:
    print(f"Warning: Could not import thinc.backends.numpy_ops: {e}")
    print("The built application may have issues with this module.")