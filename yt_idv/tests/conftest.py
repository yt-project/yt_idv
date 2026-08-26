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
    prepare_platform(config._offscreen_backend)


def pytest_report_header(config):
    return f"offscreen backend: {config._offscreen_backend}"


@pytest.fixture(scope="session")
def render_backend(request):
    """the offscreen backend selected for this test session"""
    return request.config._offscreen_backend


@pytest.fixture()
def make_rc(render_backend, request):
    """yield a factory for rendering contexts that get destroyed after the test"""

    def _make_rc(width=1024, height=1024, **kwargs):
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
