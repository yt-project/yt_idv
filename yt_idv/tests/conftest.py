import base64
import os

import pytest
import yt
from pytest_html import extras as html_extras

import yt_idv


def pytest_configure(config):
    # this will get run before all tests, before collection and
    # any opengl imports that happen within test files.
    os.environ["PYOPENGL_PLATFORM"] = "osmesa"


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
def osmesa_empty_rc():
    """yield an OSMesa empy context then destroy"""

    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)
