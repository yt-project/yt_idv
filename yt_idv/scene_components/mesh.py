import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.mesh import MeshData


class MeshRendering(SceneComponent):
    name = "mesh_rendering"
    data = traitlets.Instance(MeshData)

    def draw(self, scene, program):
        GL.glDrawElements(GL.GL_TRIANGLES, self.data.size, GL.GL_UNSIGNED_INT, None)

    def _set_uniforms(self, scene, shader_program):
        pass
