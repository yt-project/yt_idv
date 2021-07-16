import numpy
from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

setup(
    ext_modules=cythonize("yt_idv/*.pyx"),
    include_dirs=[numpy.get_include()],
)
