import pytest

from yt_idv.shader_objects import component_shaders, get_shader_combos


@pytest.mark.parametrize("render_name", component_shaders.keys())
def test_get_shader_combos_all_components(render_name):
    # default call to get_shader_combos should return all shaders
    expected = component_shaders[render_name]
    actual = get_shader_combos(render_name)
    assert set(expected) == set(actual)


def test_get_shader_combos_coord():
    # only block_rendering supports non-cartesian for now, check that the supported
    # shaders are returned as expected.
    shaders = get_shader_combos("block_rendering", coord_system="spherical")
    not_supported = ["isocontours", "slice"]
    assert all(s not in shaders for s in not_supported)
    supported = ["max_intensity", "projection", "transfer_function", "constant"]
    for s in supported:
        assert s in shaders
    assert all(s in shaders for s in supported)
