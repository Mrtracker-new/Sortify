# PyInstaller hook for thinc.backends.numpy_ops
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_data_files
import os
import sys
import importlib.util

# Collect all numpy_ops files and dependencies
datas, binaries, hiddenimports = collect_all('thinc.backends.numpy_ops')

# Add specific dependencies
hiddenimports.extend([
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.core.multiarray',
    'numpy.core.umath',
    'numpy.linalg.lapack_lite',
    'thinc.backends.ops',
])

# Try to locate the numpy_ops module and its dependencies
try:
    # First try to import numpy_ops directly
    import thinc.backends.numpy_ops
    print(f"Successfully imported thinc.backends.numpy_ops from {thinc.backends.numpy_ops.__file__}")
    
    # Get the directory containing numpy_ops
    numpy_ops_dir = os.path.dirname(thinc.backends.numpy_ops.__file__)
    print(f"numpy_ops directory: {numpy_ops_dir}")
    
    # Add the numpy_ops module itself
    module_file = thinc.backends.numpy_ops.__file__
    if module_file.endswith('.py'):
        # If it's a .py file, add it as data
        datas.append((module_file, os.path.join('thinc', 'backends')))
        print(f"Added module file: {module_file} -> thinc/backends")
    elif module_file.endswith('.pyd') or module_file.endswith('.so') or module_file.endswith('.dylib'):
        # If it's a binary module, add it as binary
        binaries.append((module_file, os.path.join('thinc', 'backends')))
        print(f"Added binary module: {module_file} -> thinc/backends")
    
    # Add any DLL files in the numpy_ops directory
    for file in os.listdir(numpy_ops_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib') or file.endswith('.pyd'):
            full_path = os.path.join(numpy_ops_dir, file)
            dest_dir = os.path.join('thinc', 'backends')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
    
    # Also add the parent directory DLLs
    parent_dir = os.path.dirname(numpy_ops_dir)
    for file in os.listdir(parent_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib') or file.endswith('.pyd'):
            full_path = os.path.join(parent_dir, file)
            dest_dir = os.path.join('thinc')
            binaries.append((full_path, dest_dir))
            print(f"Added binary from parent dir: {full_path} -> {dest_dir}")
    
    # Also add numpy core DLLs
    try:
        import numpy.core
        numpy_core_dir = os.path.dirname(numpy.core.__file__)
        print(f"numpy.core directory: {numpy_core_dir}")
        
        for file in os.listdir(numpy_core_dir):
            if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib') or file.endswith('.pyd'):
                full_path = os.path.join(numpy_core_dir, file)
                dest_dir = os.path.join('numpy', 'core')
                binaries.append((full_path, dest_dir))
                print(f"Added numpy.core binary: {full_path} -> {dest_dir}")
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not process numpy.core: {e}")
    
except ImportError as e:
    print(f"Warning: Could not import thinc.backends.numpy_ops: {e}")
    print("The built application may have issues with this module.")
    
    # Try to find the module using importlib
    try:
        import thinc
        thinc_dir = os.path.dirname(thinc.__file__)
        backends_dir = os.path.join(thinc_dir, 'backends')
        
        if os.path.exists(backends_dir):
            print(f"Found backends directory: {backends_dir}")
            
            # Look for numpy_ops.py or numpy_ops module
            numpy_ops_py = os.path.join(backends_dir, 'numpy_ops.py')
            numpy_ops_dir = os.path.join(backends_dir, 'numpy_ops')
            
            if os.path.exists(numpy_ops_py):
                datas.append((numpy_ops_py, os.path.join('thinc', 'backends')))
                print(f"Added module file: {numpy_ops_py} -> thinc/backends")
            
            if os.path.exists(numpy_ops_dir) and os.path.isdir(numpy_ops_dir):
                for file in os.listdir(numpy_ops_dir):
                    full_path = os.path.join(numpy_ops_dir, file)
                    if file.endswith('.py'):
                        datas.append((full_path, os.path.join('thinc', 'backends', 'numpy_ops')))
                        print(f"Added Python file: {full_path} -> thinc/backends/numpy_ops")
                    elif file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib') or file.endswith('.pyd'):
                        binaries.append((full_path, os.path.join('thinc', 'backends', 'numpy_ops')))
                        print(f"Added binary: {full_path} -> thinc/backends/numpy_ops")
    except Exception as e:
        print(f"Warning: Failed to locate numpy_ops module: {e}")