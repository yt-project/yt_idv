"""Tests for `yt_idv` package."""

import numpy as np
import pytest
import yt
import yt.testing
from numpy.testing import assert_equal

from yt_idv import shader_objects
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_components.curves import CurveCollectionRendering, CurveRendering
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.scene_data.curve import CurveCollection, CurveData
from yt_idv.scene_graph import SceneGraph


@pytest.fixture()
def fake_amr_rc(make_rc):
    """Return a context that has a "fake" AMR dataset added, with "radius"
    as the field.
    """
    ds = yt.testing.fake_amr_ds()
    dd = ds.all_data()
    rc = make_rc()
    rc.add_scene(dd, "radius", no_ghost=True)
    return rc


@pytest.fixture()
def empty_scene_rc(make_rc):
    """Return a context that has no dataset."""
    rc = make_rc()
    ds = yt.testing.fake_amr_ds()
    rc.add_scene(ds, None)
    rc.ds = ds
    return rc


@pytest.mark.image_test
def test_snapshots(fake_amr_rc, image_store):
    """Check that we can make some snapshots."""
    fake_amr_rc.scene.components[0].render_method = "max_intensity"
    image_store(fake_amr_rc)
    fake_amr_rc.scene.components[0].render_method = "projection"
    image_store(fake_amr_rc)
    fake_amr_rc.scene.components[0].render_method = "transfer_function"
    image_store(fake_amr_rc)
    fake_amr_rc.scene.components[0]._recompile_shader()
    image_store(fake_amr_rc)


@pytest.mark.image_test
def test_camera_position(fake_amr_rc, image_store):
    """Check that we can update the camera position"""
    vm = fake_amr_rc.scene.camera.view_matrix
    fake_amr_rc.scene.camera.set_position([0.5, 2.0, 3.0])
    # check that the view matrix has changed
    assert np.sum(np.abs(vm - fake_amr_rc.scene.camera.view_matrix)) > 0.0
    image_store(fake_amr_rc)


@pytest.mark.image_test
def test_depth_buffer_toggle(fake_amr_rc, image_store):
    fake_amr_rc.scene.components[0].use_db = True
    image_store(fake_amr_rc)


@pytest.mark.image_test
def test_slice(fake_amr_rc, image_store):
    fake_amr_rc.scene.components[0].render_method = "slice"
    fake_amr_rc.scene.components[0].slice_position = (0.5, 0.5, 0.5)
    for ax in [0, 1, 2]:
        normal = [0.0, 0.0, 0.0]
        normal[ax] = 1.0
        fake_amr_rc.scene.components[0].slice_normal = tuple(normal)
        image_store(fake_amr_rc)
    fake_amr_rc.scene.components[0].slice_normal = (1.0, 1.0, 0.0)
    fake_amr_rc.scene.components[0].slice_position = (0.5, 0.25, 0.5)
    image_store(fake_amr_rc)


def _interior_gaps(image):
    """Undrawn pixels that are enclosed by drawn pixels along both axes."""
    drawn = image[:, :, 3] > 0

    def enclosed(axis):
        forward = np.maximum.accumulate(drawn, axis=axis)
        backward = np.flip(np.maximum.accumulate(np.flip(drawn, axis), axis), axis)
        return forward & backward

    return ~drawn & enclosed(0) & enclosed(1)


@pytest.mark.parametrize("near_plane", [1e-4, 1e-2])
@pytest.mark.image_test
def test_slice_no_block_boundary_gaps(fake_amr_rc, near_plane):
    """Rays that hit a face shared by two blocks must be drawn by one of them."""
    component = fake_amr_rc.scene.components[0]
    component.render_method = "slice"
    component.slice_position = (0.5, 0.5, 0.5)
    component.slice_normal = (1.0, 1.0, 0.0)

    camera = fake_amr_rc.scene.camera
    camera.near_plane = near_plane
    camera._update_matrices()

    assert _interior_gaps(fake_amr_rc.run()).sum() == 0


@pytest.mark.image_test
def test_annotate_boxes(empty_scene_rc, image_store):
    """Check the box annotation."""
    empty_scene_rc.scene.add_box([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    image_store(empty_scene_rc)
    empty_scene_rc.scene.add_box([0.2, 0.2, 0.3], [0.8, 0.8, 0.7])
    image_store(empty_scene_rc)
    empty_scene_rc.scene.annotations[-1].box_width /= 2
    empty_scene_rc.scene.annotations[-1].box_color = (1.0, 0.0, 0.0)
    image_store(empty_scene_rc)


@pytest.mark.image_test
def test_annotate_grids(empty_scene_rc, image_store):
    """Make sure we can add some grid positions."""
    from yt_idv.scene_annotations.grid_outlines import GridOutlines  # NOQA
    from yt_idv.scene_data.grid_positions import GridPositions  # NOQA

    gp = GridPositions(grid_list=empty_scene_rc.ds.index.grids.tolist())
    empty_scene_rc.scene.data_objects.append(gp)
    go = GridOutlines(data=gp)
    empty_scene_rc.scene.components.append(go)
    image_store(empty_scene_rc)
    empty_scene_rc.scene.camera.offset_position(0.25)
    image_store(empty_scene_rc)
    empty_scene_rc.scene.camera.offset_position(0.5)
    image_store(empty_scene_rc)


@pytest.mark.image_test
def test_annotate_text(empty_scene_rc, image_store):
    """Test that text can be annotated and updated."""
    text = empty_scene_rc.scene.add_text("Origin 0 0", origin=(0.0, 0.0))
    image_store(empty_scene_rc)
    text.text = "Change text"
    image_store(empty_scene_rc)
    text.text = "Origin -0.5 -0.5"
    text.origin = (-0.5, -0.5)
    image_store(empty_scene_rc)
    text.origin = (0.0, 0.0)
    text.text = "S 1.0"
    image_store(empty_scene_rc)
    text.text = "S 2.0"
    text.scale = 2.0
    image_store(empty_scene_rc)


@pytest.mark.image_test
def test_isocontour_functionality(fake_amr_rc, image_store):
    fake_amr_rc.scene.components[0].render_method = "isocontours"
    image_store(fake_amr_rc)


@pytest.mark.image_test
def test_curves(fake_amr_rc, image_store):
    # add a single curve

    curved = CurveData()
    x1d = np.linspace(0, 1, 10)
    xyz = np.column_stack([x1d, x1d, np.zeros((10,))])
    curved.add_data(xyz)
    curve_render = CurveRendering(data=curved, curve_rgba=(1.0, 0.0, 0.0, 1.0))
    curve_render.display_name = "single streamline"
    fake_amr_rc.scene.data_objects.append(curved)
    fake_amr_rc.scene.components.append(curve_render)
    image_store(fake_amr_rc)

    curve_collection = CurveCollection()
    xyz = np.column_stack([x1d, np.zeros((10,)), x1d])
    curve_collection.add_curve(xyz)
    xyz = np.column_stack([np.zeros((10,)), x1d, x1d])
    curve_collection.add_curve(xyz)
    curve_collection.add_data()  # call add_data() after done adding curves

    cc_render = CurveCollectionRendering(
        data=curve_collection, curve_rgba=(0.2, 0.2, 0.2, 1.0)
    )
    cc_render.display_name = "multiple streamlines"
    fake_amr_rc.scene.data_objects.append(curve_collection)
    fake_amr_rc.scene.components.append(cc_render)

    image_store(fake_amr_rc)


@pytest.fixture()
def set_very_bad_shader():
    # this temporarily points the default vertex shader source file to a
    # bad shader that will raise compilation errors.
    known_shaders = shader_objects.known_shaders
    good_shader = known_shaders["vertex"]["default"]["source"]
    known_shaders["vertex"]["default"]["source"] = "bad_shader.vert.glsl"
    yield known_shaders
    known_shaders["vertex"]["default"]["source"] = good_shader


@pytest.mark.image_test
def test_bad_shader(empty_scene_rc, set_very_bad_shader):
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
@pytest.mark.image_test
def test_shader_programs(empty_scene_rc, shader_name):
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


@pytest.mark.image_test
def test_camera_dict_update(fake_amr_rc):
    pos = [0.5, 2.0, 3.0]
    fake_amr_rc.scene.camera.set_position(pos)

    cdict = fake_amr_rc.scene.camera.dict()
    assert_equal(cdict["position"], pos)

    fake_amr_rc.scene.camera.set_position([4.0, 4.0, 4])
    fake_amr_rc.scene.camera.update(**cdict)
    assert_equal(fake_amr_rc.scene.camera.position, pos)


@pytest.mark.image_test
def test_block_collection_grid_ids(make_rc):
    rc = make_rc()
    ds = yt.testing.fake_amr_ds()
    wid = ds.domain_width / 20.0 / 2.0
    c = ds.domain_center
    reg = ds.region(c, c - wid, c + wid)
    rc.add_scene(reg, ("stream", "Density"), no_ghost=True)

    block_coll = rc.scene.data_objects[0]
    gl = block_coll.grid_id_list
    assert len(gl) < len(ds.index.grids)
    grids = block_coll.intersected_grids
    assert len(grids) == len(gl)


@pytest.mark.image_test
def test_manual_scene_graph(make_rc, image_store):
    rc = make_rc()
    ds = yt.testing.fake_amr_ds()

    c = TrackballCamera.from_dataset(ds)
    rc.scene = SceneGraph(camera=c)
    rc.scene.data_objects.append(BlockCollection(data_source=ds.all_data()))
    rc.scene.data_objects[-1].add_data(("radius"), no_ghost=True)
    rc.scene.components.append(BlockRendering(data=rc.scene.data_objects[-1]))

    image_store(rc)


@pytest.mark.image_test
def test_block_collection_min_max(make_rc, image_store):
    rc = make_rc()
    ds = yt.testing.fake_amr_ds()

    c = TrackballCamera.from_dataset(ds)
    rc.scene = SceneGraph(camera=c)
    rc.scene.data_objects.append(
        BlockCollection(
            data_source=ds.all_data(),
            compute_min_max=False,
            min_val=0.0,
            max_val=10.0,
        )
    )
    rc.scene.data_objects[-1].add_data(("stream", "Density"), no_ghost=True)
    rc.scene.components.append(BlockRendering(data=rc.scene.data_objects[-1]))

    image_store(rc)
