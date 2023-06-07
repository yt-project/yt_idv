import numpy
from setuptools import setup

from Cython.Build import cythonize  # isort:skip

setup(
    ext_modules=cythonize("yt_idv/*.pyx"),
    include_dirs=[numpy.get_include()],
)
