import numpy
from setuptools import setup

from Cython.Build import cythonize  # isort:skip

_include_dirs = [numpy.get_include()]

setup(ext_modules=cythonize("yt_idv/utilities/*.pyx"), include_dirs=_include_dirs)
