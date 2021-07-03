import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.particle_positions import ParticlePositions


class ParticleRendering(SceneComponent):
    name = "particle_rendering"
    data = traitlets.Instance(ParticlePositions)
    scale = traitlets.CFloat(1.0)

    def render_gui(self, imgui, renderer, scene):
        changed = super(ParticleRendering, self).render_gui(imgui, renderer, scene)
        _, new_value = imgui.slider_float("Scale", self.scale, 0.0, 10.0)
        if _:
            self.scale = new_value
            changed = True
        if imgui.button("Recompile Shader"):
            self.fragment_shader.delete_shader()
            if self.geometry_shader:
                self.geometry_shader.delete_shader()
            self.vertex_shader.delete_shader()
            self.colormap_fragment.delete_shader()
            self.colormap_vertex.delete_shader()
            self._program1_invalid = self._program2_invalid = True
            changed = True
        return changed

    def draw(self, scene, program):
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glDrawArrays(GL.GL_POINTS, 0, self.data.size)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("scale", self.scale)
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
