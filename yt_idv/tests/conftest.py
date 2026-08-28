import base64
import os

import pytest
import yt
from pytest_html import extras as html_extras

import yt_idv
from yt_idv.rendering_contexts import prepare_platform

BACKENDS = ("osmesa", "egl", "pyglet")

# a hidden pyglet window still needs to be told not to show itself or build a gui
_BACKEND_KWARGS = {"pyglet": {"visible": False, "gui": False}}


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


@pytest.fixture(scope="session")
def render_backend(request):
    """the offscreen backend selected for this test session"""
    return request.config._offscreen_backend


@pytest.fixture()
def make_rc(render_backend, request):
    """yield a factory for rendering contexts that get destroyed after the test"""

    def _make_rc(width=None, height=None, **kwargs):
        default_width, default_height = request.config._canvas_size
        width = default_width if width is None else width
        height = default_height if height is None else height
        kwargs = {**_BACKEND_KWARGS.get(render_backend, {}), **kwargs}
        rc = yt_idv.render_context(render_backend, width=width, height=height, **kwargs)
        request.addfinalizer(rc.close)
        return rc

    return _make_rc


@pytest.fixture()
def image_store(request, extras, tmpdir):
    def _snap_image(rc):
        image = rc.run()
        img = yt.write_bitmap(image, None)
        content = base64.b64encode(img).decode("ascii")
        extras.append(html_extras.png(content))
        extras.append(html_extras.html("<br clear='all'/>"))

    return _snap_image


@pytest.fixture()
def empty_rc(make_rc):
    """an empty rendering context"""
    return make_rc()
