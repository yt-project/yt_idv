#!/usr/bin/env python

"""The setup script."""

from setuptools import Extension, find_packages, setup  # NOQA
from Cython.Build import cythonize
import numpy

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()

requirements = [
    "Click>=7.0",
    "yt>=4.0.dev0",
    "traitlets>=5.0.5",
    "pyOpenGL>=3.1.5",
    "traittypes>=0.2.1",
    "matplotlib>=3.0",
    "numpy>=1.18.0",
    "pyglet>=2.0.dev0",
    "pyyaml>=5.3.1",
    "imgui>=1.2.0",
]

setup_requirements = ["pytest-runner", "cython>=0.29"]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Matthew Turk",
    author_email="matthewturk@gmail.com",
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Interactive Volume Rendering for yt",
    entry_points={"console_scripts": ["yt_idv=yt_idv.cli:main",],},
    install_requires=requirements,
    license="BSD license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="yt_idv",
    name="yt_idv",
    packages=find_packages(include=["yt_idv", "yt_idv.*"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/data-exp-lab/yt_idv",
    version="0.2.0",
    zip_safe=False,
    ext_modules=cythonize("yt_idv/*.pyx"),
    include_dirs=[numpy.get_include()],
)
