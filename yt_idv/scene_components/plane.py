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

    def draw(self, scene, program):
        with self.data.texture_object.bind(0):
            GL.glDisable(GL.GL_CULL_FACE)  # default, two-sided rendering
            GL.glDrawElements(GL.GL_TRIANGLES, self.data.size, GL.GL_UNSIGNED_INT, None)
            GL.glEnable(GL.GL_CULL_FACE)  # back to what it was

    def _set_uniforms(self, scene, shader_program):
        cam = scene.camera
        shader_program._set_uniform("projection", cam.projection_matrix)
        shader_program._set_uniform("modelview", cam.view_matrix)
        shader_program._set_uniform("to_worldview", self.data.to_worldview)

    def render_gui(self, imgui, renderer, scene):
        changed, self.visible = imgui.checkbox("Visible", self.visible)
        _ = take_log_checkbox(imgui, self)
        changed = changed or _
        _ = colormap_list(imgui, self)
        changed = changed or _
        return changed
