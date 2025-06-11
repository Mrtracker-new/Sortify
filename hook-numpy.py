from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('numpy')

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
    'numpy.core._dtype_ctypes'
])