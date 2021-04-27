import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.plane import PlaneData


class Plane(SceneComponent):
    name = "image_plane"
    data = traitlets.Instance(PlaneData)
    _plane_data_uniforms = ["plane_pt", "basis_u", "basis_v"]

    def draw(self, scene, program):

        # this is where the texture binding goes
        # tex_id = self.data.texture_id
        the_tex = self.data.the_texture
        with the_tex.bind(0):
            # for tex_ind, _tex, _bitmap_tex in self.data.viewpoint_iter(scene.camera):
            #     GL.glDrawArrays(GL.GL_TRIANGLES, tex_ind * each, each)
            GL.glDrawElements(GL.GL_TRIANGLES, self.data.size, GL.GL_UNSIGNED_INT, None)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        for attstr in self._plane_data_uniforms:
            shader_program._set_uniform(attstr, getattr(self.data, attstr))
