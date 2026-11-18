import math

import numpy as np
import traitlets
from OpenGL import GL
from yt.utilities.lib.pixelization_routines import SPHKernelInterpolationTable

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.particle_positions import ParticlePositions
from yt_idv.shader_objects import component_shaders, get_shader_combos

from ..opengl_support import Texture1D

KERNEL_TYPES = [
    "cubic",
    "quartic",
    "quintic",
    "wendland2",
    "wendland4",
    "wendland6",
    "flat",
]

# q^2 at the texel centers of the kernel texture, so that linear filtering
# returns the table value at exactly the sampled q^2
_Q2_TEXEL_CENTERS = (np.arange(256) + 0.5) / 256


class SPHRendering(SceneComponent):
    name = "sph_rendering"
    data = traitlets.Instance(ParticlePositions)
    scale = traitlets.CFloat(1.0).tag(config=True)
    max_particle_size = traitlets.CFloat(1e-3).tag(config=True)
    kernel_name = traitlets.Unicode("cubic").tag(config=True)
    kernel_table = traitlets.Instance(SPHKernelInterpolationTable, allow_none=True)
    interpolation_texture = traitlets.Instance(Texture1D)

    @traitlets.observe("kernel_name")
    def _change_kernel_name(self, change):
        if change["new"] == "flat":
            self.kernel_table = None
            flat = np.ones(256, dtype="f4")
            flat[-1] = 0.0
            self.interpolation_texture = Texture1D(data=flat)
            return
        self.kernel_table = SPHKernelInterpolationTable(change["new"])
        values = self.kernel_table.interpolate_array(_Q2_TEXEL_CENTERS)
        self.interpolation_texture = Texture1D(data=values.astype("f4"))

    @traitlets.default("kernel_table")
    def _default_kernel_table(self):
        if self.kernel_name is None:
            return
        return SPHKernelInterpolationTable(self.kernel_name)

    @traitlets.default("interpolation_texture")
    def _default_interpolation_texture(self):
        if self.kernel_table is None and self.kernel_name == "flat":
            flat = np.ones(256, dtype="f4")
            flat[-1] = 0.0
            return Texture1D(data=flat)
        values = self.kernel_table.interpolate_array(_Q2_TEXEL_CENTERS)
        return Texture1D(data=values.astype("f4"))

    def render_gui(self, imgui, renderer, scene):
        changed = super().render_gui(imgui, renderer, scene)
        _, kernel_index = imgui.listbox(
            "Kernel", KERNEL_TYPES.index(self.kernel_name), KERNEL_TYPES
        )
        if _:
            self.kernel_name = KERNEL_TYPES[kernel_index]
        changed = changed or _
        valid_shaders = get_shader_combos(self.name)
        descriptions = [
            component_shaders[self.name][_]["description"] for _ in valid_shaders
        ]
        selected = valid_shaders.index(self.render_method)
        _, shader_ind = imgui.listbox("Shader", selected, descriptions)
        if _:
            self.render_method = valid_shaders[shader_ind]
        changed = changed or _
        _, new_value = imgui.slider_float(
            "Log Scale", math.log10(self.scale), -8.0, 2.0
        )
        if _:
            self.scale = 10**new_value
            changed = True
        imgui.text("Filter Particle Max Size")
        _, new_value = imgui.slider_float(
            "max-size", 1.0 / self.max_particle_size, 1.0, 100.0
        )
        if _:
            self.max_particle_size = 1.0 / new_value
            changed = True
        return changed

    def draw(self, scene, program):
        if self.render_method == "max_intensity":
            # the max blend would clamp negative values to the default zero
            # clear; alpha stays 0 so uncovered pixels are still discarded
            lowest = np.finfo("f4").min
            GL.glClearBufferfv(
                GL.GL_COLOR, 0, np.array([lowest, lowest, lowest, 0.0], "f4")
            )
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
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
