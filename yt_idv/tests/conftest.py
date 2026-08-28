import base64

import pytest
import yt
from pytest_html import extras as html_extras

import yt_idv

# the CLI options and pytest_configure/pytest_report_header hooks that
# select the backend and canvas size live in the rootdir conftest.py

# a hidden pyglet window still needs to be told not to show itself or build a gui
_BACKEND_KWARGS = {"pyglet": {"visible": False, "gui": False}}


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
