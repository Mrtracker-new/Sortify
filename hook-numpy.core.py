# PyInstaller hook for numpy.core
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_submodules
import os
import sys

# Collect all numpy.core files and dependencies
datas, binaries, hiddenimports = collect_all('numpy.core')

# Collect all DLLs from numpy.core
numpy_core_dlls = collect_dynamic_libs('numpy.core')
binaries.extend(numpy_core_dlls)

# Add all numpy.core submodules
hiddenimports.extend(collect_submodules('numpy.core'))

# Add specific numpy.core modules that might be missing
hiddenimports.extend([
    'numpy.core._multiarray_umath',
    'numpy.core.multiarray',
    'numpy.core.umath',
    'numpy.core._dtype_ctypes',
    'numpy.core._multiarray_tests',
    'numpy.core._operand_flag_tests',
    'numpy.core._rational_tests',
    'numpy.core._struct_ufunc_tests',
    'numpy.core._umath_tests',
])

# Ensure numpy.core DLLs are included
try:
    import numpy.core
    print(f"Successfully imported numpy.core from {numpy.core.__file__}")
    
    # Get the directory containing numpy.core
    numpy_core_dir = os.path.dirname(numpy.core.__file__)
    print(f"numpy.core directory: {numpy_core_dir}")
    
    # Add any DLL files in this directory
    for file in os.listdir(numpy_core_dir):
        if file.endswith('.dll') or file.endswith('.so') or file.endswith('.dylib') or file.endswith('.pyd'):
            full_path = os.path.join(numpy_core_dir, file)
            dest_dir = os.path.join('numpy', 'core')
            binaries.append((full_path, dest_dir))
            print(f"Added binary: {full_path} -> {dest_dir}")
    
    # Try to import specific modules and add their DLLs
    try:
        import numpy.core._multiarray_umath
        multiarray_umath_file = numpy.core._multiarray_umath.__file__
        print(f"Found _multiarray_umath at: {multiarray_umath_file}")
        binaries.append((multiarray_umath_file, os.path.join('numpy', 'core')))
        print(f"Added _multiarray_umath binary: {multiarray_umath_file} -> numpy/core")
    except ImportError as e:
        print(f"Warning: Could not import numpy.core._multiarray_umath: {e}")
    
    # Also check for other important modules
    modules_to_check = [
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.core._dtype_ctypes',
        'numpy.core._multiarray_tests',
        'numpy.core._operand_flag_tests',
        'numpy.core._rational_tests',
        'numpy.core._struct_ufunc_tests',
        'numpy.core._umath_tests',
    ]
    
    for module_name in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[''])
            if hasattr(module, '__file__'):
                module_file = module.__file__
                print(f"Found {module_name} at: {module_file}")
                if module_file.endswith('.dll') or module_file.endswith('.so') or module_file.endswith('.dylib') or module_file.endswith('.pyd'):
                    binaries.append((module_file, os.path.join('numpy', 'core')))
                    print(f"Added {module_name} binary: {module_file} -> numpy/core")
        except ImportError as e:
            print(f"Warning: Could not import {module_name}: {e}")
            
except ImportError as e:
    print(f"Warning: Could not import numpy.core: {e}")
    print("The built application may have issues with this module.")