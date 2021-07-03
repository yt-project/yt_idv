import math

import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.particle_positions import ParticlePositions


class ParticleRendering(SceneComponent):
    name = "particle_rendering"
    data = traitlets.Instance(ParticlePositions)
    scale = traitlets.CFloat(1.0)
    max_particle_size = traitlets.CFloat(1e-3)

    def render_gui(self, imgui, renderer, scene):
        changed = super(ParticleRendering, self).render_gui(imgui, renderer, scene)
        _, new_value = imgui.slider_float(
            "Log Scale", math.log10(self.scale), -8.0, 2.0
        )
        if _:
            self.scale = 10 ** new_value
            changed = True
        if imgui.button("Reset Colorbounds"):
            self.cmap_min = self.cmap_max = None
            changed = True
        _, self.cmap_log = imgui.checkbox("Take log", self.cmap_log)
        changed = changed or _
        _, new_value = imgui.slider_float(
            "Max Inverse Fractional Size", 1.0 / self.max_particle_size, 10.0, 10000.0
        )
        if _:
            self.max_particle_size = 1.0 / new_value
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
        # We should batch this rendering somehow, and
        # also figure out the right face culling
        GL.glDrawArrays(GL.GL_POINTS, 0, self.data.size)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("scale", self.scale)
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        shader_program._set_uniform("max_particle_size", self.max_particle_size)
