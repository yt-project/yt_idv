import pytest

from yt_idv.scene_components.particles import ParticleRendering
from yt_idv.shader_objects import (
    PreprocessorDefinitionState,
    _validate_shader,
    known_shaders,
)


def test_preprocessor_definition_state():

    pds = PreprocessorDefinitionState()

    pds.add_definition("fragment", ("USE_DB", ""))
    assert ("USE_DB", "") in pds["fragment"]
    pds.add_definition("vertex", ("placeholder", ""))
    assert ("placeholder", "") in pds["vertex"]

    with pytest.raises(ValueError, match="shader_type must be"):
        pds.add_definition("not_a_shader_type", ("any_str", ""))

    pds.clear_definition("fragment", ("USE_DB", ""))
    assert ("USE_DB", "") not in pds["fragment"]

    pds.reset("vertex")
    assert len(pds.vertex) == 0

    pds.add_definition("fragment", ("USE_DB", ""))
    pds.add_definition("geometry", ("placeholder", ""))
    pds.add_definition("vertex", ("placeholder", ""))
    pds.reset()
    for shadertype in pds._valid_shader_types:
        assert len(pds._get_dict(shadertype)) == 0


def test_preprocessor_definitions_are_not_shared():
    with_defs = _validate_shader(
        "fragment", "apply_colormap", preprocessor_defs=[("USE_DB", "")]
    )
    without_defs = _validate_shader("fragment", "apply_colormap")
    assert with_defs.preprocessor_defs == [("USE_DB", "")]
    assert without_defs.preprocessor_defs == []
    assert "preprocessor_defs" not in known_shaders["fragment"]["apply_colormap"]


@pytest.mark.image_test
def test_component_definitions_do_not_leak(empty_rc):
    first = ParticleRendering()
    first.use_db = True
    assert ("USE_DB", "") in first.colormap_fragment.preprocessor_defs

    second = ParticleRendering()
    assert second.colormap_fragment.shader_name == "apply_colormap"
    assert ("USE_DB", "") not in second.colormap_fragment.preprocessor_defs
