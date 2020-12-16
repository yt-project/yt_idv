#!/usr/bin/env python

"""Tests for `yt_idv` package."""

import base64
import os

import pytest
import yt
from pytest_html import extras

import yt_idv

os.environ["PYOPENGL_PLATFORM"] = "osmesa"


@pytest.fixture()
def osmesa_fake_amr():
    """Return an OSMesa context that has a "fake" AMR dataset added, with "radius"
    as the field.
    """
    ds = yt.testing.fake_amr_ds()
    dd = ds.all_data()
    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    rc.add_scene(dd, "radius", no_ghost=True)
    return rc


@pytest.fixture()
def osmesa_empty():
    """Return an OSMesa context that has no dataset.
    """
    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    ds = yt.testing.fake_amr_ds()
    rc.add_scene(ds, None)
    rc.ds = ds
    return rc


@pytest.fixture()
def image_store(request, extra, tmpdir):
    def _snap_image(rc):
        image = rc.run()
        img = yt.write_bitmap(image, None)
        content = base64.b64encode(img).decode("ascii")
        extra.append(extras.png(content))
        extra.append(extras.html("<br clear='all'/>"))

    return _snap_image


def test_snapshots(osmesa_fake_amr, image_store):
    """Check that we can make some snapshots."""
    osmesa_fake_amr.scene.components[0].render_method = "max_intensity"
    image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0].render_method = "projection"
    image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0].render_method = "transfer_function"
    image_store(osmesa_fake_amr)


def test_annotate_boxes(osmesa_empty, image_store):
    """Check the box annotation."""
    osmesa_empty.scene.add_box([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    image_store(osmesa_empty)
    osmesa_empty.scene.add_box([0.2, 0.2, 0.3], [0.8, 0.8, 0.7])
    image_store(osmesa_empty)
    osmesa_empty.scene.annotations[-1].box_width /= 2
    osmesa_empty.scene.annotations[-1].box_color = (1.0, 0.0, 0.0)
    image_store(osmesa_empty)


def test_annotate_grids(osmesa_empty, image_store):
    """Make sure we can add some grid positions."""
    from yt_idv.scene_annotations.grid_outlines import GridOutlines  # NOQA
    from yt_idv.scene_data.grid_positions import GridPositions  # NOQA

    gp = GridPositions(grid_list=osmesa_empty.ds.index.grids.tolist())
    osmesa_empty.scene.data_objects.append(gp)
    go = GridOutlines(data=gp)
    osmesa_empty.scene.components.append(go)
    image_store(osmesa_empty)
    osmesa_empty.scene.camera.offset_position(0.25)
    image_store(osmesa_empty)
    osmesa_empty.scene.camera.offset_position(0.5)
    image_store(osmesa_empty)


def test_annotate_text(osmesa_empty, image_store):
    """Test that text can be annotated and updated."""
    text = osmesa_empty.scene.add_text("Origin 0 0", origin=(0.0, 0.0))
    image_store(osmesa_empty)
    text.text = "Change text"
    image_store(osmesa_empty)
    text.text = "Origin -0.5 -0.5"
    text.origin = (-0.5, -0.5)
    image_store(osmesa_empty)
    text.origin = (0.0, 0.0)
    text.text = "S 1.0"
    image_store(osmesa_empty)
    text.text = "S 2.0"
    text.scale = 2.0
    image_store(osmesa_empty)
