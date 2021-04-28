import traitlets
from OpenGL import GL

from yt_idv.scene_components.base_component import SceneComponent, _cmaps
from yt_idv.scene_data.plane import BasePlane


def take_log_checkbox(imgui, scene_obj):
    # imgui UI element for setting the log boolean
    changed, scene_obj.cmap_log = imgui.checkbox("Take log", scene_obj.cmap_log)
    return changed


def colormap_list(imgui, scene_obj):
    # imgui UI element for colormap list and selection
    changed, cmap_index = imgui.listbox(
        "Colormap", _cmaps.index(scene_obj.colormap.colormap_name), _cmaps
    )
    if changed:
        scene_obj.colormap.colormap_name = _cmaps[cmap_index]
    return changed


class Plane(SceneComponent):
    name = "image_plane"
    data = traitlets.Instance(BasePlane)
    _plane_data_uniforms = ["plane_pt", "north_vec", "east_vec"]

    def draw(self, scene, program):
        the_tex = self.data.the_texture
        with the_tex.bind(0):
            GL.glDrawElements(GL.GL_TRIANGLES, self.data.size, GL.GL_UNSIGNED_INT, None)

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        for attstr in self._plane_data_uniforms:
            shader_program._set_uniform(attstr, getattr(self.data, attstr))

    def render_gui(self, imgui, renderer):
        changed = super().render_gui(imgui, renderer)
        ui_changes = [
                        take_log_checkbox(imgui, self),
                        colormap_list(imgui, self),
                     ]
        changed = changed or any(ui_changes)
