import numpy
from setuptools import Extension, find_packages, setup

from Cython.Build import cythonize  # isort:skip

setup(
    ext_modules=cythonize("yt_idv/*.pyx"),
    include_dirs=[numpy.get_include()],
)
