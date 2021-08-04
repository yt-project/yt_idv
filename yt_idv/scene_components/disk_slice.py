import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.sliced_values import SlicedData


class DiskSlice(SceneComponent):
    name = "disk_slice"
    data = traitlets.Instance(SlicedData)
    r_bounds = traitlets.Tuple((0.0, 1.0), trait=traitlets.CFloat())
    theta_bounds = traitlets.Tuple((0.0, 2.0 * np.pi), trait=traitlets.CFloat())
    phi_bounds = traitlets.Tuple((0.0, np.pi), trait=traitlets.CFloat())
    center = traitlets.Tuple((0.5, 0.5, 0.5), trait=traitlets.CFloat())
    disk_vector = traitlets.Tuple((1.0, 0.0, 0.0), trait=traitlets.CFloat())

    def render_gui(self, imgui, renderer, scene):
        changed = super(DiskSlice, self).render_gui(imgui, renderer, scene)
        for val, (mi, ma) in (
            ("r", (0.0, 1.0)),
            ("theta", (0.0, 2.0 * np.pi)),
            ("phi", (0.0, np.pi)),
        ):
            vals = getattr(self, f"{val}_bounds")
            _, new_lower = imgui.slider_float2(val, vals[0], vals[1], mi, ma)
            if _:
                setattr(self, f"{val}_bounds", new_lower)
                changed = True
        return changed

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glDrawArraysInstanced(GL.GL_TRIANGLE_STRIP, 0, 4, self.data.size)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("r_bounds", np.array(self.r_bounds))
        shader_program._set_uniform("theta_bounds", np.array(self.theta_bounds))
        shader_program._set_uniform("phi_bounds", np.array(self.phi_bounds))
        shader_program._set_uniform("disk_center", np.array(self.center))
        shader_program._set_uniform("disk_vector", np.array(self.disk_vector))
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        shader_program._set_uniform(
            "inv_pmvm", np.linalg.inv(cam.projection_matrix @ cam.view_matrix)
        )
