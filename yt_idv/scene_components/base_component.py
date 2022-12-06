import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.constants import FULLSCREEN_QUAD
from yt_idv.gui_support import add_popup_help
from yt_idv.opengl_support import (
    ColormapTexture,
    Framebuffer,
    VertexArray,
    VertexAttribute,
)
from yt_idv.scene_data.base_data import SceneData
from yt_idv.shader_objects import (
    ShaderProgram,
    ShaderTrait,
    component_shaders,
    default_shader_combos,
)

_cmaps = ["arbre", "viridis", "magma", "doom"]
_buffers = ["frame", "depth"]


class SceneComponent(traitlets.HasTraits):
    data = traitlets.Instance(SceneData)
    base_quad = traitlets.Instance(SceneData)
    name = "undefined"
    priority = traitlets.CInt(0)
    visible = traitlets.Bool(True)
    use_db = traitlets.Bool(False)  # use depth buffer
    iso_tolerance = traitlets.CFloat(0.025)
    iso_layers = traitlets.List()
    display_bounds = traitlets.Tuple(
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        default_value=(0.0, 1.0, 0.0, 1.0),
    )
    clear_region = traitlets.Bool(False)

    render_method = traitlets.Unicode(allow_none=True)
    fragment_shader = ShaderTrait(allow_none=True).tag(shader_type="fragment")
    geometry_shader = ShaderTrait(allow_none=True).tag(shader_type="geometry")
    vertex_shader = ShaderTrait(allow_none=True).tag(shader_type="vertex")
    fb = traitlets.Instance(Framebuffer)
    colormap_fragment = ShaderTrait(allow_none=True).tag(shader_type="fragment")
    colormap_vertex = ShaderTrait(allow_none=True).tag(shader_type="vertex")
    colormap = traitlets.Instance(ColormapTexture)
    _program1 = traitlets.Instance(ShaderProgram, allow_none=True)
    _program2 = traitlets.Instance(ShaderProgram, allow_none=True)
    _program1_invalid = True
    _program2_invalid = True
    _cmap_bounds_invalid = True

    # These attributes are
    cmap_min = traitlets.CFloat(None, allow_none=True)
    cmap_max = traitlets.CFloat(None, allow_none=True)
    cmap_log = traitlets.Bool(False)
    scale = traitlets.CFloat(1.0)

    @traitlets.observe("display_bounds")
    def _change_display_bounds(self, change):
        # We need to update the framebuffer if the width or height has changed
        # Same thing is true if the total pixel size has changed, but that is
        # not doable from in here.
        if change["old"] == traitlets.Undefined:
            return
        old_width = change["old"][1] - change["old"][0]
        old_height = change["old"][3] - change["old"][2]
        new_width = change["new"][1] - change["new"][0]
        new_height = change["new"][3] - change["new"][2]
        if old_width != new_width or old_height != new_height:
            self.fb = Framebuffer()

    def render_gui(self, imgui, renderer, scene):
        changed, self.visible = imgui.checkbox("Visible", self.visible)
        _, self.use_db = imgui.checkbox("Depth Buffer", self.use_db)
        changed = changed or _
        _ = add_popup_help(
            imgui, "If checked, will render the depth buffer of the current view."
        )
        changed = changed or _
        _, self.iso_tolerance = imgui.slider_float(
            "Isocontour Tolerance", self.iso_tolerance, 0.0, 0.1
        )
        changed = changed or _

        if self.render_method == "isocontours":
            if imgui.button("Add Layer"):
                if len(self.iso_layers) < 32:
                    changed = True
                    self.iso_layers.append(0.0)
            _ = self._construct_isolayer_table(imgui)
            changed = changed or _

        if imgui.button("Recompile Shader"):
            changed = self._recompile_shader()
        _, cmap_index = imgui.listbox(
            "Colormap", _cmaps.index(self.colormap.colormap_name), _cmaps
        )
        if _:
            self.colormap.colormap_name = _cmaps[cmap_index]
        changed = changed or _
        _ = add_popup_help(imgui, "Select the colormap to use for the rendering.")
        changed = changed or _
        _, self.cmap_log = imgui.checkbox("Take log", self.cmap_log)
        changed = changed or _
        _ = add_popup_help(
            imgui, "If checked, the rendering will use log-normalized values."
        )
        changed = changed or _
        if imgui.button("Reset Colorbounds"):
            self._cmap_bounds_invalid = True
            changed = True
        _ = add_popup_help(imgui, "Click to reset the colorbounds of the current view.")
        changed = changed or _

        return changed

    @traitlets.default("render_method")
    def _default_render_method(self):
        return default_shader_combos[self.name]

    @traitlets.observe("render_method")
    def _change_render_method(self, change):
        new_combo = component_shaders[self.name][change["new"]]
        with self.hold_trait_notifications():
            self.vertex_shader = new_combo["first_vertex"]
            self.fragment_shader = new_combo["first_fragment"]
            self.geometry_shader = new_combo.get("first_geometry", None)
            self.colormap_vertex = new_combo["second_vertex"]
            self.colormap_fragment = new_combo["second_fragment"]

    @traitlets.observe("render_method")
    def _add_initial_isolayer(self, change):
        # this adds an initial isocontour entry when the render method
        # switches to isocontours and if there are no layers yet.
        if change["new"] == "isocontours" and len(self.iso_layers) == 0:
            self.iso_layers.append(0.0)

    @traitlets.default("fb")
    def _fb_default(self):
        return Framebuffer()

    @traitlets.observe("fragment_shader")
    def _change_fragment(self, change):
        # Even if old/new are the same
        self._program1_invalid = True

    @traitlets.observe("vertex_shader")
    def _change_vertex(self, change):
        # Even if old/new are the same
        self._program1_invalid = True

    @traitlets.observe("geometry_shader")
    def _change_geometry(self, change):
        self._program1_invalid = True

    @traitlets.observe("colormap_vertex")
    def _change_colormap_vertex(self, change):
        # Even if old/new are the same
        self._program2_invalid = True

    @traitlets.observe("colormap_fragment")
    def _change_colormap_fragment(self, change):
        # Even if old/new are the same
        self._program2_invalid = True

    @traitlets.observe("use_db")
    def _initialize_db(self, changed):
        # invaldiate the colormap when the depth buffer selection changes
        self._cmap_bounds_invalid = True

    @traitlets.default("colormap")
    def _default_colormap(self):
        cm = ColormapTexture()
        cm.colormap_name = "arbre"
        return cm

    @traitlets.default("vertex_shader")
    def _vertex_shader_default(self):
        return component_shaders[self.name][self.render_method]["first_vertex"]

    @traitlets.default("fragment_shader")
    def _fragment_shader_default(self):
        return component_shaders[self.name][self.render_method]["first_fragment"]

    @traitlets.default("geometry_shader")
    def _geometry_shader_default(self):
        _ = component_shaders[self.name][self.render_method]
        return _.get("first_geometry", None)

    @traitlets.default("colormap_vertex")
    def _colormap_vertex_default(self):
        return component_shaders[self.name][self.render_method]["second_vertex"]

    @traitlets.default("colormap_fragment")
    def _colormap_fragment_default(self):
        return component_shaders[self.name][self.render_method]["second_fragment"]

    @traitlets.default("base_quad")
    def _default_base_quad(self):
        bq = SceneData(
            name="fullscreen_quad",
            vertex_array=VertexArray(name="tri", each=6),
        )
        fq = FULLSCREEN_QUAD.reshape((6, 3), order="C")
        bq.vertex_array.attributes.append(
            VertexAttribute(name="vertexPosition_modelspace", data=fq)
        )
        return bq

    @property
    def program1(self):
        if self._program1_invalid:
            if self._program1 is not None:
                self._program1.delete_program()
            self._fragment_shader_default()
            self._program1 = ShaderProgram(
                self.vertex_shader, self.fragment_shader, self.geometry_shader
            )
            self._program1_invalid = False
        return self._program1

    @property
    def program2(self):
        if self._program2_invalid:
            if self._program2 is not None:
                self._program2.delete_program()
            # The vertex shader will always be the same.
            # The fragment shader will change based on whether we are
            # colormapping or not.
            self._program2 = ShaderProgram(self.colormap_vertex, self.colormap_fragment)
            self._program2_invalid = False
        return self._program2

    def run_program(self, scene):
        # Store this info, because we need to render into a framebuffer that is the
        # right size.
        x0, y0, w, h = GL.glGetIntegerv(GL.GL_VIEWPORT)
        GL.glViewport(0, 0, w, h)
        if not self.visible:
            return
        with self.fb.bind(True):
            with self.program1.enable() as p:
                scene.camera._set_uniforms(scene, p)
                self._set_uniforms(scene, p)
                p._set_uniform("iso_tolerance", float(self.iso_tolerance))
                p._set_uniform("iso_num_layers", int(len(self.iso_layers)))
                v = np.zeros(32, dtype="float32")
                v[: len(self.iso_layers)] = self._get_sanitized_iso_layers()
                p._set_uniform("iso_layers", v)
                p._set_uniform("iso_log", bool(self.cmap_log))
                p._set_uniform("iso_min", float(self.data.min_val))
                p._set_uniform("iso_max", float(self.data.max_val))
                with self.data.vertex_array.bind(p):
                    self.draw(scene, p)

        if self._cmap_bounds_invalid:
            self._reset_cmap_bounds()

        with self.colormap.bind(0):
            with self.fb.input_bind(1, 2):
                with self.program2.enable() as p2:
                    with scene.bind_buffer():
                        p2._set_uniform("cmap", 0)
                        p2._set_uniform("fb_tex", 1)
                        p2._set_uniform("db_tex", 2)
                        p2._set_uniform("use_db", self.use_db)
                        # Note that we use cmap_min/cmap_max, not
                        # self.cmap_min/self.cmap_max.
                        p2._set_uniform("cmap_min", self.cmap_min)
                        p2._set_uniform("cmap_max", self.cmap_max)
                        p2._set_uniform("cmap_log", float(self.cmap_log))
                        with self.base_quad.vertex_array.bind(p2):
                            # Now we do our viewport globally, not just within
                            # the framebuffer
                            GL.glViewport(x0, y0, w, h)
                            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

    def draw(self, scene, program):
        raise NotImplementedError

    def _get_sanitized_iso_layers(self):
        return self.iso_layers

    def _recompile_shader(self) -> bool:
        # removes existing shaders, invalidates shader programs
        shaders = (
            "vertex_shader",
            "geometry_shader",
            "fragment_shader",
            "colormap_vertex",
            "colormap_fragment",
        )
        for shader_name in shaders:
            s = getattr(self, shader_name, None)
            if s:
                s.delete_shader()
        self._program1_invalid = self._program2_invalid = True
        return True

    def _construct_isolayer_table(self, imgui) -> bool:

        imgui.columns(2, "iso_layers_cols", False)
        i = 0
        changed = False
        while i < len(self.iso_layers):
            _, self.iso_layers[i] = imgui.input_float(
                "Layer " + str(i + 1),
                self.iso_layers[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            imgui.next_column()
            if imgui.button("Remove##rl" + str(i + 1)):
                self.iso_layers.pop(i)
                i -= 1
                _ = True
            changed = changed or _
            imgui.next_column()
            i += 1
        imgui.columns(1)

        return changed

    def _reset_cmap_bounds(self):
        data = self.fb.data
        if self.use_db:
            data[:, :, :3] = self.fb.depth_data[:, :, None]
        data = data[data[:, :, 3] > 0][:, 0]
        if data.size > 0:
            self.cmap_min = data.min()
            self.cmap_max = data.max()
        if data.size == 0:
            self.cmap_min = 0.0
            self.cmap_max = 1.0
        else:
            print(f"Computed new cmap values {self.cmap_min} - {self.cmap_max}")
        self._cmap_bounds_invalid = False
