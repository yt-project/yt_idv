import math

import numpy as np
import traitlets
from OpenGL import GL
from yt.utilities.lib.pixelization_routines import SPHKernelInterpolationTable

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.particle_positions import ParticlePositions

from ..opengl_support import Texture1D


class ParticleRendering(SceneComponent):
    name = "particle_rendering"
    data = traitlets.Instance(ParticlePositions)
    scale = traitlets.CFloat(1.0)
    max_particle_size = traitlets.CFloat(1e-3)
    kernel_name = traitlets.Unicode("cubic")
    kernel_table = traitlets.Instance(SPHKernelInterpolationTable)
    interpolation_texture = traitlets.Instance(Texture1D)

    @traitlets.observe("kernel_name")
    def _change_kernel_name(self, change):
        self.kernel_table = SPHKernelInterpolationTable(change["new"])
        values = self.kernel_table.interpolate_array(np.mgrid[0.0:1.0:256j])
        self.interpolation_texture = Texture1D(data=values.astype("f4"))

    @traitlets.default("kernel_table")
    def _default_kernel_table(self):
        return SPHKernelInterpolationTable(self.kernel_name)

    @traitlets.default("interpolation_texture")
    def _default_interpolation_texture(self):
        values = self.kernel_table.interpolate_array(np.mgrid[0.0:1.0:256j])
        return Texture1D(data=values.astype("f4"))

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
            "Max Inverse Fractional Size", 1.0 / self.max_particle_size, 1.0, 10000.0
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
        with self.interpolation_texture.bind(0):
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
