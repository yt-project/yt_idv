# pytest only registers CLI options from "initial" conftests. A bare
# `pytest` invocation (no path arguments) loads only the rootdir conftest
# before argument parsing, so the options and their hooks must live here
# rather than next to the test-directory fixtures.
import os

import pytest

from yt_idv.rendering_contexts import prepare_platform

BACKENDS = ("osmesa", "egl", "pyglet")


def pytest_addoption(parser):
    parser.addoption(
        "--offscreen-backend",
        choices=BACKENDS,
        default=None,
        help="offscreen rendering backend to run the test suite against",
    )
    parser.addini(
        "offscreen_backend",
        help="default offscreen rendering backend, if --offscreen-backend is unset",
        default="osmesa",
    )
    parser.addoption(
        "--canvas-width",
        type=int,
        default=1024,
        help="default width of offscreen rendering canvases",
    )
    parser.addoption(
        "--canvas-height",
        type=int,
        default=1024,
        help="default height of offscreen rendering canvases",
    )


def _resolve_backend(config):
    backend = config.getoption("--offscreen-backend")
    if backend is not None:
        return backend

    source = "YT_IDV_TEST_BACKEND"
    backend = os.environ.get(source)
    if backend is None:
        source = "offscreen_backend"
        backend = config.getini(source) or "osmesa"

    if backend not in BACKENDS:
        raise pytest.UsageError(f"{source}={backend!r} is not one of {BACKENDS}")
    return backend


def pytest_configure(config):
    # this will get run before all tests, before collection and
    # any opengl imports that happen within test files.
    config._offscreen_backend = _resolve_backend(config)
    config._canvas_size = (
        config.getoption("--canvas-width"),
        config.getoption("--canvas-height"),
    )
    prepare_platform(config._offscreen_backend)


def pytest_report_header(config):
    width, height = config._canvas_size
    return (
        f"offscreen backend: {config._offscreen_backend}, "
        f"default canvas size: {width}x{height}"
    )
