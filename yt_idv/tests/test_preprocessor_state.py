import pytest

from yt_idv.shader_objects import PreprocessorDefinitionState


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
