#!/usr/bin/env python

"""Tests for `yt_idv` package."""

import os

import pytest
import yt

import yt_idv

os.environ["PYOPENGL_PLATFORM"] = "egl"


@pytest.fixture()
def egl_fake_amr():
    """Return an EGL context that has a "fake" AMR dataset added, with "radius"
    as the field.
    """
    ds = yt.testing.fake_amr_ds()
    dd = ds.all_data()
    rc = yt_idv.render_context("egl", width=1024, height=1024)
    rc.add_scene(dd, "radius", no_ghost=True)
    return rc


@pytest.fixture()
def egl_empty():
    """Return an EGL context that has no dataset.
    """
    rc = yt_idv.render_context("egl", width=1024, height=1024)
    return rc


def test_snapshots(egl_fake_amr):
    """Check that we can make some snapshots."""
    image = egl_fake_amr.run()
    yt.write_bitmap(image, "test.png")
