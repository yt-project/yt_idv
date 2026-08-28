"""Wiring needed to drive Mesa's EGL on macOS.

macOS ships no EGL of its own, so headless rendering there means using a Mesa
build (homebrew's ``mesa``, for example).  Three things have to be arranged, all
of them before ``OpenGL.platform`` is imported:

* Mesa's EGL defaults to the X11 platform, which needs a running XQuartz
  server.  ``EGL_PLATFORM=surfaceless`` selects the platform that works without
  a display server.
* PyOpenGL finds its libraries through ``ctypes.util.find_library``, whose macOS
  search path does not include Homebrew, so importing ``OpenGL.platform`` under
  ``PYOPENGL_PLATFORM=egl`` fails outright -- that import resolves ``libEGL``
  eagerly.  ``find_library`` reads ``DYLD_FALLBACK_LIBRARY_PATH`` at call time,
  so putting the Mesa directory there first is enough to fix the lookup.
* That is not enough for GL itself: PyOpenGL's EGL platform asks for
  ``"OpenGL"`` before ``"GL"``, and the first name always hits Apple's
  ``OpenGL.framework``, which knows nothing about the EGL context we are about
  to make current.  So ``GL`` is replaced on the platform object with Mesa's
  ``libGL`` loaded by absolute path.
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

_WRONG_PLATFORM_MSG = """\
PyOpenGL is already using a non-EGL platform, so its GL entry points are bound
to Apple's OpenGL.framework and cannot be used with an EGL context. Build the
EGL render context before anything imports OpenGL.\
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


def _prepend_dyld_path(directory):
    key = "DYLD_FALLBACK_LIBRARY_PATH"
    entries = [entry for entry in os.environ.get(key, "").split(":") if entry]
    if directory in entries:
        return
    if not entries:
        # setting the variable replaces dyld's implicit default, so spell it out
        entries = [str(Path.home() / "lib"), "/usr/local/lib", "/lib", "/usr/lib"]
    os.environ[key] = ":".join([directory, *entries])


def configure_mesa_egl():
    """Point PyOpenGL's EGL platform at a Mesa GL/EGL pair.

    Must be called before anything imports ``OpenGL.platform``.  A no-op off
    macOS.
    """
    if sys.platform != "darwin":
        return

    os.environ.setdefault("EGL_PLATFORM", "surfaceless")

    paths = {}
    for name in ("EGL", "GL"):
        found = _find_dylib(name)
        if found is None:
            raise ImportError(_NOT_FOUND_MSG.format(name=name))
        paths[name] = found

    # Importing OpenGL.platform under PYOPENGL_PLATFORM=egl resolves libEGL
    # eagerly, through ctypes.util.find_library -- which reads
    # DYLD_FALLBACK_LIBRARY_PATH at call time and otherwise never looks in
    # Homebrew.  This has to be in place before that import happens.
    _prepend_dyld_path(str(Path(paths["EGL"]).parent))

    from OpenGL import platform

    if type(platform.PLATFORM).__name__ != "EGLPlatform":
        raise ImportError(_WRONG_PLATFORM_MSG)

    # find_library("OpenGL") resolves to Apple's framework even now, and
    # PyOpenGL tries that name before "GL", so GL still needs replacing.
    for name, path in paths.items():
        bound = platform.PLATFORM.__dict__.get(name)
        if bound is not None and not getattr(bound, "_name", "").startswith("/System/"):
            continue
        setattr(platform.PLATFORM, name, ctypes.CDLL(path, ctypes.RTLD_GLOBAL))
