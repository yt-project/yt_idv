"""Wiring needed to drive Mesa's EGL on macOS.

macOS ships no EGL of its own, so headless rendering there means using a Mesa
build (homebrew's ``mesa``, for example).  Two things have to be arranged before
``OpenGL.GL`` is imported:

* Mesa's EGL defaults to the X11 platform, which needs a running XQuartz
  server.  ``EGL_PLATFORM=surfaceless`` selects the platform that works without
  a display server.
* PyOpenGL's EGL platform resolves its GL entry points by asking
  ``ctypes.util.find_library`` for ``"OpenGL"`` before ``"GL"``.  On macOS the
  first name always hits Apple's ``OpenGL.framework``, which knows nothing about
  the EGL context we just made current, so every GL call would land in the wrong
  library.  Loading the Mesa dylibs by absolute path and assigning them onto the
  platform object sidesteps that lookup entirely.
"""

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path

_LIB_SUBDIRS = ("lib", "opt/mesa/lib")
_PREFIXES = ("/opt/homebrew", "/usr/local", "/opt/local")

_NOT_FOUND_MSG = """\
Could not locate Mesa's lib{name}.dylib, which yt_idv needs for headless EGL
rendering on macOS. Install Mesa (e.g. `brew install mesa`), or point yt_idv at
an existing install by setting YT_IDV_MESA_PREFIX to the directory that holds
lib/lib{name}.dylib.\
"""

_APPLE_GL_MSG = """\
PyOpenGL has already bound {name} to Apple's OpenGL.framework, which cannot be
used with an EGL context. Build the EGL render context before anything imports
OpenGL.GL.\
"""


def _candidate_dirs():
    prefixes = [
        os.environ.get("YT_IDV_MESA_PREFIX"),
        os.environ.get("CONDA_PREFIX"),
        *_PREFIXES,
    ]
    for prefix in prefixes:
        if not prefix:
            continue
        for subdir in _LIB_SUBDIRS:
            yield Path(prefix) / subdir
    for entry in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "").split(":"):
        if entry:
            yield Path(entry)


def _find_dylib(name):
    for directory in _candidate_dirs():
        candidate = directory / f"lib{name}.dylib"
        if candidate.exists():
            return str(candidate)
    found = ctypes.util.find_library(name)
    if found is not None and not found.startswith("/System/"):
        return found
    return None


def configure_mesa_egl():
    """Bind PyOpenGL's EGL platform to a Mesa GL/EGL pair.

    Must be called before anything imports ``OpenGL.GL``.  A no-op off macOS.
    """
    if sys.platform != "darwin":
        return

    os.environ.setdefault("EGL_PLATFORM", "surfaceless")

    from OpenGL import platform

    for name in ("EGL", "GL"):
        already_bound = platform.PLATFORM.__dict__.get(name)
        if already_bound is not None:
            if getattr(already_bound, "_name", "").startswith("/System/"):
                raise ImportError(_APPLE_GL_MSG.format(name=name))
            continue
        path = _find_dylib(name)
        if path is None:
            raise ImportError(_NOT_FOUND_MSG.format(name=name))
        setattr(platform.PLATFORM, name, ctypes.CDLL(path, ctypes.RTLD_GLOBAL))
