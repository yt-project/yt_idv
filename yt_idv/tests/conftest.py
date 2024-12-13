import base64
import os

import pytest
import yt
from pytest_html import extras as html_extras


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
