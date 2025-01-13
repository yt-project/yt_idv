"""Tests for `yt_idv` package."""

import numpy as np
import pytest
import yt
import yt.testing

import yt_idv
from yt_idv import shader_objects
from yt_idv.scene_components.curves import CurveCollectionRendering, CurveRendering
from yt_idv.scene_data.curve import CurveCollection, CurveData


@pytest.fixture()
def osmesa_fake_amr():
    """Return an OSMesa context that has a "fake" AMR dataset added, with "radius"
    as the field.
    """
    ds = yt.testing.fake_amr_ds()
    dd = ds.all_data()
    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    rc.add_scene(dd, "radius", no_ghost=True)
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)


@pytest.fixture()
def osmesa_empty():
    """Return an OSMesa context that has no dataset."""
    rc = yt_idv.render_context("osmesa", width=1024, height=1024)
    ds = yt.testing.fake_amr_ds()
    rc.add_scene(ds, None)
    rc.ds = ds
    yield rc
    rc.osmesa.OSMesaDestroyContext(rc.context)


def test_snapshots(osmesa_fake_amr, image_store):
    """Check that we can make some snapshots."""
    osmesa_fake_amr.scene.components[0].render_method = "max_intensity"
    image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0].render_method = "projection"
    image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0].render_method = "transfer_function"
    image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0]._recompile_shader()
    image_store(osmesa_fake_amr)


def test_camera_position(osmesa_fake_amr, image_store):
    """Check that we can update the camera position"""
    vm = osmesa_fake_amr.scene.camera.view_matrix
    osmesa_fake_amr.scene.camera.set_position([0.5, 2.0, 3.0])
    # check that the view matrix has changed
    assert np.sum(np.abs(vm - osmesa_fake_amr.scene.camera.view_matrix)) > 0.0
    image_store(osmesa_fake_amr)


def test_depth_buffer_toggle(osmesa_fake_amr, image_store):
    osmesa_fake_amr.scene.components[0].use_db = True
    image_store(osmesa_fake_amr)


def test_slice(osmesa_fake_amr, image_store):
    osmesa_fake_amr.scene.components[0].render_method = "slice"
    osmesa_fake_amr.scene.components[0].slice_position = (0.5, 0.5, 0.5)
    for ax in [0, 1, 2]:
        normal = [0.0, 0.0, 0.0]
        normal[ax] = 1.0
        osmesa_fake_amr.scene.components[0].slice_normal = tuple(normal)
        image_store(osmesa_fake_amr)
    osmesa_fake_amr.scene.components[0].slice_normal = (1.0, 1.0, 0.0)
    osmesa_fake_amr.scene.components[0].slice_position = (0.5, 0.25, 0.5)
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


def test_isocontour_functionality(osmesa_fake_amr, image_store):
    osmesa_fake_amr.scene.components[0].render_method = "isocontours"
    image_store(osmesa_fake_amr)


def test_curves(osmesa_fake_amr, image_store):
    # add a single curve

    curved = CurveData()
    x1d = np.linspace(0, 1, 10)
    xyz = np.column_stack([x1d, x1d, np.zeros((10,))])
    curved.add_data(xyz)
    curve_render = CurveRendering(
        data=curved, curve_rgba=(1.0, 0.0, 0.0, 1.0), line_width=4
    )
    curve_render.display_name = "single streamline"
    osmesa_fake_amr.scene.data_objects.append(curved)
    osmesa_fake_amr.scene.components.append(curve_render)
    image_store(osmesa_fake_amr)

    curve_collection = CurveCollection()
    xyz = np.column_stack([x1d, np.zeros((10,)), x1d])
    curve_collection.add_curve(xyz)
    xyz = np.column_stack([np.zeros((10,)), x1d, x1d])
    curve_collection.add_curve(xyz)
    curve_collection.add_data()  # call add_data() after done adding curves

    cc_render = CurveCollectionRendering(
        data=curve_collection, curve_rgba=(0.2, 0.2, 0.2, 1.0), line_width=4
    )
    cc_render.display_name = "multiple streamlines"
    osmesa_fake_amr.scene.data_objects.append(curve_collection)
    osmesa_fake_amr.scene.components.append(cc_render)

    image_store(osmesa_fake_amr)


@pytest.fixture()
def set_very_bad_shader():
    # this temporarily points the default vertex shader source file to a
    # bad shader that will raise compilation errors.
    known_shaders = shader_objects.known_shaders
    good_shader = known_shaders["vertex"]["default"]["source"]
    known_shaders["vertex"]["default"]["source"] = "bad_shader.vert.glsl"
    yield known_shaders
    known_shaders["vertex"]["default"]["source"] = good_shader


def test_bad_shader(osmesa_empty, set_very_bad_shader):
    # this test is meant to check that a bad shader would indeed be caught
    # by the subsequent test_shader_programs test.
    shader_name = "box_outline"
    program = shader_objects.component_shaders[shader_name]["default"]

    vertex_shader = shader_objects._validate_shader(
        "vertex", program["first_vertex"], allow_null=False
    )
    fragment_shader = shader_objects._validate_shader(
        "fragment", program["first_fragment"], allow_null=False
    )
    with pytest.raises(RuntimeError, match="shader complilation error"):
        _ = shader_objects.ShaderProgram(vertex_shader, fragment_shader, None)


@pytest.mark.parametrize("shader_name", list(shader_objects.component_shaders.keys()))
def test_shader_programs(osmesa_empty, shader_name):
    for program in shader_objects.component_shaders[shader_name].values():

        vertex_shader = shader_objects._validate_shader(
            "vertex", program["first_vertex"], allow_null=False
        )
        assert isinstance(vertex_shader, shader_objects.Shader)
        fragment_shader = shader_objects._validate_shader(
            "fragment", program["first_fragment"], allow_null=False
        )
        assert isinstance(fragment_shader, shader_objects.Shader)
        geometry_shader = program.get("first_geometry", None)
        if geometry_shader is not None:
            geometry_shader = shader_objects._validate_shader(
                "geometry", geometry_shader, allow_null=False
            )
            assert isinstance(geometry_shader, shader_objects.Shader)

        _ = shader_objects.ShaderProgram(
            vertex_shader, fragment_shader, geometry_shader
        )

        colormap_vertex = shader_objects._validate_shader(
            "vertex", program["second_vertex"], allow_null=False
        )
        assert isinstance(colormap_vertex, shader_objects.Shader)
        colormap_fragment = shader_objects._validate_shader(
            "fragment", program["second_fragment"], allow_null=False
        )
        assert isinstance(colormap_fragment, shader_objects.Shader)
        _ = shader_objects.ShaderProgram(colormap_vertex, colormap_fragment)
