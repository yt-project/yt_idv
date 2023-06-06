import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.variable_mesh import VariableMeshContainer


class VariableMeshDisplay(SceneComponent):
    """
    A class that renders variable mesh datasets.
    """

    name = "variable_mesh_display"
    data = traitlets.Instance(VariableMeshContainer)
    priority = 11

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glDrawArraysInstanced(GL.GL_TRIANGLE_STRIP, 0, 4, self.data.size)

    def _set_uniforms(self, scene, program):
        pass
