from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs  # type: ignore

datas, binaries, hiddenimports = collect_all('numpy')

# Collect all DLLs from numpy
numpy_dlls = collect_dynamic_libs('numpy')
binaries.extend(numpy_dlls)

# Add specific NumPy modules that might be missing
hiddenimports.extend([
    'numpy.core._multiarray_umath',
    'numpy.random.common',
    'numpy.random.bounded_integers',
    'numpy.random.entropy',
    'numpy.random.mtrand',
    'numpy.random._pickle',
    'numpy.random._sfc64',
    'numpy.random._philox',
    'numpy.random._pcg64',
    'numpy.random._mt19937',
    'numpy.random._bit_generator',
    'numpy.random._generator',
    'numpy.linalg.lapack_lite',
    'numpy.core._dtype_ctypes',
    'numpy.core._multiarray_tests',
    'numpy.core._operand_flag_tests',
    'numpy.core._rational_tests',
    'numpy.core._struct_ufunc_tests',
    'numpy.core._umath_tests',
    'numpy.fft._pocketfft_internal',
    'numpy.linalg._umath_linalg',
    'numpy.polynomial._polybase',
    'numpy.random._common',
    'numpy.random._bounded_integers',
    'numpy.random._mt19937',
    'numpy.random._pcg64',
    'numpy.random._philox',
    'numpy.random._sfc64'
])

# Verify critical NumPy modules are importable at build time
try:
    import numpy.core._multiarray_umath  # type: ignore
    import numpy.linalg.lapack_lite  # type: ignore
    print("Successfully imported critical NumPy modules")
except ImportError as e:
    print(f"Warning: Could not import some NumPy modules: {e}")
    print("The built application may have issues with these modules.")