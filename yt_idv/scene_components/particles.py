import math

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.particle_positions import ParticlePositions


class ParticleRendering(SceneComponent):
    name = "particle_rendering"
    data = traitlets.Instance(ParticlePositions)
    scale = traitlets.CFloat(1e-3)
    max_particle_size = traitlets.CFloat(1e-3)

    def render_gui(self, imgui, renderer, scene):
        changed = super(ParticleRendering, self).render_gui(imgui, renderer, scene)
        _, new_value = imgui.slider_float(
            "Log Scale", math.log10(self.scale), -8.0, 2.0
        )
        if _:
            self.scale = 10 ** new_value
            changed = True
        imgui.text("Filter Particle Max Size")
        _, new_value = imgui.slider_float("", 1.0 / self.max_particle_size, 1.0, 100.0)
        if _:
            self.max_particle_size = 1.0 / new_value
            changed = True
        return changed

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glDrawArraysInstanced(GL.GL_TRIANGLE_STRIP, 0, 4, self.data.size)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("scale", self.scale)
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        shader_program._set_uniform("max_particle_size", self.max_particle_size)
        shader_program._set_uniform(
            "inv_pmvm", np.linalg.inv(cam.projection_matrix @ cam.view_matrix)
        )
