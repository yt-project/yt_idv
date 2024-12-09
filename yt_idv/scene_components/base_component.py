import numpy as np
import traitlets
from OpenGL import GL

from yt_idv._cmyt_utilities import cmyt_names
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
    PreprocessorDefinitionState,
    ShaderProgram,
    ShaderTrait,
    component_shaders,
    default_shader_combos,
)

_cmaps = ["arbre", "viridis", "magma", "doom", "cividis", "plasma", "RdBu", "coolwarm"]
_cmaps += [f"{_}_r" for _ in _cmaps]
# add in all the cmyt colormaps too! this will include the reversed maps too.
_cmaps += cmyt_names
_cmaps.sort(key=lambda v: v.lower())
_buffers = ["frame", "depth"]


class SceneComponent(traitlets.HasTraits):
    data = traitlets.Instance(SceneData)
    base_quad = traitlets.Instance(SceneData)
    name = "undefined"
    priority = traitlets.CInt(0)
    visible = traitlets.Bool(True)
    use_db = traitlets.Bool(False)  # use depth buffer
    iso_tolerance = traitlets.CFloat(-1)  # the tolerance for finding isocontours
    iso_tol_is_pct = traitlets.Bool(False)  # if True, the tolerance is a fraction
    iso_log = traitlets.Bool(True)  # if True, iso values are base 10 exponents
    iso_layers = traitlets.List()  # the target values for isocontours
    iso_layers_alpha = traitlets.List()  # the transparency of isocontours
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
    _program1_pp_defs = traitlets.Instance(PreprocessorDefinitionState, allow_none=True)
    _program2_pp_defs = traitlets.Instance(PreprocessorDefinitionState, allow_none=True)
    _program1_invalid = True
    _program2_invalid = True
    _cmap_bounds_invalid = True

    display_name = traitlets.Unicode(allow_none=True)

    final_pass_vertex = ShaderTrait(allow_none=True).tag(shader_type="vertex")
    final_pass_fragment = ShaderTrait(allow_none=True).tag(shader_type="fragment")
    _final_pass = traitlets.Instance(ShaderProgram, allow_none=True)
    _final_pass_invalid = True

    # These attributes are just for colormap application
    cmap_min = traitlets.CFloat(None, allow_none=True)
    cmap_max = traitlets.CFloat(None, allow_none=True)
    cmap_log = traitlets.Bool(True)
    scale = traitlets.CFloat(1.0)

    # This attribute determines whether or not this component is "active"
    active = traitlets.Bool(True)

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
        _ = add_popup_help(
            imgui, "If checked, will render the depth buffer of the current view."
        )
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

        if self.render_method == "isocontours":
            _ = self._render_isolayer_inputs(imgui)
            changed = changed or _

        return changed

    @traitlets.observe("iso_log")
    def _switch_iso_log(self, change):
        # if iso_log, then the user is setting 10**x, otherwise they are setting
        # x directly. So when toggling this checkbox we convert the existing
        # values between the two forms.
        if change["old"]:
            # if True, we were taking the log, but now are not:
            self.iso_tolerance = 10**self.iso_tolerance
            new_iso_layers = [10**iso_val for iso_val in self.iso_layers]
            self.iso_layers = new_iso_layers
        else:
            # we were not taking the log but now we are, so convert to the exponent
            self.iso_tolerance = np.log10(self.iso_tolerance)
            new_iso_layers = [np.log10(iso_val) for iso_val in self.iso_layers]
            self.iso_layers = new_iso_layers

    @traitlets.default("display_name")
    def _default_display_name(self):
        return self.name

    @traitlets.default("render_method")
    def _default_render_method(self):
        return default_shader_combos[self.name]

    @traitlets.default("_program1_pp_defs")
    def _default_program1_pp_defs(self):
        return PreprocessorDefinitionState()

    @traitlets.default("_program2_pp_defs")
    def _default_program2_pp_defs(self):
        return PreprocessorDefinitionState()

    @traitlets.observe("render_method")
    def _change_render_method(self, change):
        new_combo = component_shaders[self.name][change["new"]]
        with self.hold_trait_notifications():
            self.vertex_shader = (
                new_combo["first_vertex"],
                self._program1_pp_defs["vertex"],
            )
            self.fragment_shader = (
                new_combo["first_fragment"],
                self._program1_pp_defs["fragment"],
            )
            self.geometry_shader = (
                new_combo.get("first_geometry", None),
                self._program1_pp_defs["geometry"],
            )
            self.colormap_vertex = (
                new_combo["second_vertex"],
                self._program2_pp_defs["vertex"],
            )
            self.colormap_fragment = (
                new_combo["second_fragment"],
                self._program2_pp_defs["fragment"],
            )

    @traitlets.observe("render_method")
    def _add_initial_isolayer(self, change):
        # this adds an initial isocontour entry when the render method
        # switches to isocontours and if there are no layers yet.
        if change["new"] == "isocontours" and len(self.iso_layers) == 0:
            self.iso_layers.append(0.0)
            self.iso_layers_alpha.append(1.0)

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
    def _toggle_depth_buffer(self, changed):
        # invalidate the colormap when the depth buffer selection changes
        self._cmap_bounds_invalid = True

        # update the preprocessor state: USE_DB only present in the second
        # program, only update that one.
        if changed["new"]:
            self._program2_pp_defs.add_definition("fragment", ("USE_DB", ""))
        else:
            self._program2_pp_defs.clear_definition("fragment", ("USE_DB", ""))

        # update the colormap fragment with current render method
        current_combo = component_shaders[self.name][self.render_method]
        pp_defs = self._program2_pp_defs["fragment"]
        self.colormap_fragment = current_combo["second_fragment"], pp_defs
        self._recompile_shader()

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

    @traitlets.default("final_pass_vertex")
    def _final_pass_vertex_default(self):
        return "passthrough"

    @traitlets.default("final_pass_fragment")
    def _final_pass_fragment_default(self):
        return "display_border"

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
                self.vertex_shader,
                self.fragment_shader,
                self.geometry_shader,
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
            self._program2 = ShaderProgram(
                self.colormap_vertex,
                self.colormap_fragment,
            )
            self._program2_invalid = False
        return self._program2

    @property
    def final_pass(self):
        if self._final_pass_invalid:
            if self._final_pass is not None:
                self._final_pass.delete_program()
            self._final_pass = ShaderProgram(
                self.final_pass_vertex, self.final_pass_fragment
            )
        return self._final_pass

    def _set_iso_uniforms(self, p):
        # these could be handled better by watching traits.
        p._set_uniform("iso_num_layers", int(len(self.iso_layers)))
        isolayervals = self._get_sanitized_iso_layers()
        p._set_uniform("iso_layers", isolayervals)
        p._set_uniform("iso_layer_tol", self._get_sanitized_iso_tol())
        avals = np.zeros((32,), dtype="float32")
        avals[: len(self.iso_layers)] = np.array(self.iso_layers_alpha)
        p._set_uniform("iso_alphas", avals)
        p._set_uniform("iso_min", float(self.data.min_val))
        p._set_uniform("iso_max", float(self.data.max_val))

    def run_program(self, scene):
        # Store this info, because we need to render into a framebuffer that is the
        # right size.
        if self.display_bounds != (0.0, 1.0, 0.0, 1.0):
            draw_boundary = 0.002
        else:
            draw_boundary = 0.0
        x0, y0, w, h = GL.glGetIntegerv(GL.GL_VIEWPORT)
        GL.glViewport(0, 0, w, h)
        if not self.visible:
            return
        with self.fb.bind(True):
            with self.program1.enable() as p:
                scene.camera._set_uniforms(scene, p)
                self._set_uniforms(scene, p)
                if self.render_method == "isocontours":
                    self._set_iso_uniforms(p)
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

        if draw_boundary > 0.0:
            with self.final_pass.enable() as p3:
                p3._set_uniform("draw_boundary", float(draw_boundary))
                if self.active:
                    boundary_color = np.array([0.0, 0.0, 1.0, 1.0], dtype="float32")
                else:
                    boundary_color = np.array([0.5, 0.5, 0.5, 1.0], dtype="float32")
                p3._set_uniform("boundary_color", boundary_color)
                with self.base_quad.vertex_array.bind(p3):
                    GL.glViewport(x0, y0, w, h)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

    def draw(self, scene, program):
        raise NotImplementedError

    def _get_sanitized_iso_layers(self, normalize=True):
        # returns an array of the isocontour layer values, padded with 0s out
        # to max number of contours (32).
        iso_vals = np.asarray(self.iso_layers)
        if self.iso_log:
            iso_vals = 10**iso_vals

        if normalize:
            iso_vals = self.data._normalize_by_min_max(iso_vals)

        full_array = np.zeros(32, dtype="float32")
        full_array[: len(self.iso_layers)] = iso_vals
        return full_array

    def _get_sanitized_iso_tol(self):
        # isocontour selection conditions:
        #
        # absolute difference
        #   d - c <= eps
        # or percent difference
        #   (d - c) / c * 100 <= eps_pct
        #
        # where d is a raw data value, c is the target isocontour, eps
        # is an absolute difference, eps_f is a percent difference
        #
        # The data textures available on the shaders are normalized values:
        #   d_ = (d - min) / (max - min)
        # where max and min are the global min and max values across the entire
        # volume (e.g., over all blocks, not within a block)
        #
        # So in terms of normalized values, the absoulte difference condition
        # becomes
        #   d_ - c_ <= eps / (max - min)
        # where c_ is the target value normalized in the same way as d_.
        #
        # And the percent difference becomes
        #   (d_ - c_) * (max - min) / c * 100 <= eps_pct
        #       or
        #   d_ - c_ <= eps_pct / 100 * c / (max - min)
        # so that the allowed tolerance is a function of the raw target value
        # and so will vary with each layer.

        if self.iso_log:
            # the tol value is an exponent, convert
            tol = 10 ** float(self.iso_tolerance)
        else:
            tol = float(self.iso_tolerance)
        # always normalize tolerance
        tol = tol / self.data.val_range

        if self.iso_tol_is_pct:
            # tolerance depends on the layer value
            tol = tol * 0.01
            raw_layers = self._get_sanitized_iso_layers(normalize=False)
            final_tol = raw_layers * tol
        else:
            final_tol = np.full((32,), tol, dtype="float32")
        return final_tol

    def _recompile_shader(self) -> bool:
        # removes existing shaders, invalidates shader programs
        shaders = (
            "vertex_shader",
            "geometry_shader",
            "fragment_shader",
            "colormap_vertex",
            "colormap_fragment",
            "final_pass_vertex",
            "final_pass_fragment",
        )
        for shader_name in shaders:
            s = getattr(self, shader_name, None)
            if s:
                s.delete_shader()
        self._program1_invalid = self._program2_invalid = self._final_pass_invalid = (
            True
        )
        return True

    def _render_isolayer_inputs(self, imgui) -> bool:
        changed = False
        if imgui.tree_node("Isocontours"):
            _, self.iso_log = imgui.checkbox("set exponent", self.iso_log)
            _ = add_popup_help(
                imgui, "If checked, will treat isocontour values as base-10 exponents."
            )
            changed = changed or _

            imgui.columns(2, "iso_tol_cols", False)

            _, self.iso_tolerance = imgui.input_float(
                "tol",
                self.iso_tolerance,
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The tolerance for selecting an isocontour.")
            changed = changed or _

            imgui.next_column()
            _, self.iso_tol_is_pct = imgui.checkbox("%", self.iso_tol_is_pct)
            _ = add_popup_help(imgui, "If checked, the tolerance is a percent.")
            changed = changed or _
            imgui.columns(1)

            if imgui.button("Add Layer"):
                if len(self.iso_layers) < 32:
                    changed = True
                    self.iso_layers.append(0.0)
                    self.iso_layers_alpha.append(1.0)
            _ = self._construct_isolayer_table(imgui)
            changed = changed or _
            imgui.tree_pop()
        return changed

    def _construct_isolayer_table(self, imgui) -> bool:
        imgui.columns(3, "iso_layers_cols", False)

        i = 0
        changed = False
        while i < len(self.iso_layers):
            _, self.iso_layers[i] = imgui.input_float(
                f"Layer {i + 1}",
                self.iso_layers[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The value of the isocontour layer.")
            changed = changed or _

            imgui.next_column()
            _, self.iso_layers_alpha[i] = imgui.input_float(
                f"alpha {i}",
                self.iso_layers_alpha[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The opacity of the isocontour layer.")
            changed = changed or _

            imgui.next_column()
            if imgui.button("Remove##rl" + str(i + 1)):
                self.iso_layers.pop(i)
                self.iso_layers_alpha.pop(i)
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
