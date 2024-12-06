import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.gui_support import add_popup_help
from yt_idv.opengl_support import TransferFunctionTexture
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.block_collection import BlockCollection


class Isolayers(SceneComponent):
    name = "block_isocontours"
    render_method = "isocontours"

    data = traitlets.Instance(BlockCollection)
    iso_tol_is_pct = traitlets.Bool(True)  # if True, the tolerance is a fraction
    iso_log = traitlets.Bool(True)  # if True, iso values are base 10 exponents
    iso_tolerance = traitlets.List()  # the tolerance for finding isocontours
    iso_layers = traitlets.List()  # the target values for isocontours
    iso_layers_alpha = traitlets.List()  # the transparency of isocontours
    box_width = traitlets.CFloat(0.1)
    sample_factor = traitlets.CFloat(1.0)
    transfer_function = traitlets.Instance(TransferFunctionTexture)
    tf_min = traitlets.CFloat(0.0)
    tf_max = traitlets.CFloat(1.0)
    tf_log = traitlets.Bool(True)

    @traitlets.observe("iso_log")
    def _switch_iso_log(self, change):
        # if iso_log, then the user is setting 10**x, otherwise they are setting
        # x directly. So when toggling this checkbox we convert the existing
        # values between the two forms.
        if change["old"]:
            # if True, we were taking the log, but now are not:
            new_tol = [10**iso_tol for iso_tol in self.iso_tolerance]
            self.iso_tolerance = new_tol
            new_iso_layers = [10**iso_val for iso_val in self.iso_layers]
            self.iso_layers = new_iso_layers
        else:
            # we were not taking the log but now we are, so convert to the exponent
            new_tol = [np.log10(iso_tol) for iso_tol in self.iso_tolerance]
            self.iso_tolerance = new_tol
            new_iso_layers = [np.log10(iso_val) for iso_val in self.iso_layers]
            self.iso_layers = new_iso_layers

    @traitlets.default("iso_layers")
    def _default_iso_layer(self):
        val = (self.data.min_val + self.data.max_val) / 2.0
        if self.iso_log:
            val = np.log10(val)
        return [
            val,
        ]

    @traitlets.default("iso_tolerance")
    def _default_iso_layer_tol(self):
        return [
            0.0,
        ]

    @traitlets.default("iso_layers_alpha")
    def _default_iso_layers_alpha(self):
        return [
            1.0,
        ]

    def _set_uniforms(self, scene, shader_program):

        shader_program._set_uniform("iso_num_layers", int(len(self.iso_layers)))
        isolayervals = self._get_sanitized_iso_layers()
        shader_program._set_uniform("iso_layers_min", isolayervals[0])
        shader_program._set_uniform("iso_layers_max", isolayervals[1])
        avals = np.zeros((32,), dtype="float32")
        avals[: len(self.iso_layers)] = np.array(self.iso_layers_alpha)
        shader_program._set_uniform("iso_alphas", avals)

        shader_program._set_uniform("box_width", self.box_width)
        shader_program._set_uniform("sample_factor", self.sample_factor)
        shader_program._set_uniform("ds_tex", np.array([0, 0, 0, 0, 0, 0]))
        shader_program._set_uniform("bitmap_tex", 1)
        shader_program._set_uniform("tf_tex", 2)
        shader_program._set_uniform("tf_min", self.tf_min)
        shader_program._set_uniform("tf_max", self.tf_max)
        shader_program._set_uniform("tf_log", float(self.tf_log))

    def render_gui(self, imgui, renderer, scene):
        changed = False

        _, self.iso_log = imgui.checkbox("set exponent", self.iso_log)
        _ = add_popup_help(
            imgui, "If checked, will treat isocontour values as base-10 exponents."
        )
        changed = changed or _

        imgui.next_column()
        _, self.iso_tol_is_pct = imgui.checkbox(
            "set tolerance in %", self.iso_tol_is_pct
        )
        _ = add_popup_help(imgui, "If checked, the tolerance is a percent.")
        changed = changed or _
        imgui.columns(1)

        if imgui.button("Add Layer"):
            if len(self.iso_layers) < 32:
                changed = True
                self.iso_layers.append(0.0)
                self.iso_layers_alpha.append(1.0)
                self.iso_tolerance.append(0.0)
        _ = self._construct_isolayer_table(imgui)
        changed = changed or _

        _ = super().render_gui(imgui, renderer, scene)
        changed = changed or _

        return changed

    def _construct_isolayer_table(self, imgui) -> bool:
        imgui.columns(4, "iso_layers_cols", False)
        if len(self.iso_layers) > 0:
            # column text headers
            imgui.text("Value")
            imgui.next_column()
            imgui.text("Tolerance")
            imgui.next_column()
            imgui.text("alpha")
            imgui.next_column()
            imgui.text("delete")
            imgui.next_column()

        i = 0
        changed = False
        while i < len(self.iso_layers):
            _, self.iso_layers[i] = imgui.input_float(
                f"##layer_{i}",
                self.iso_layers[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The value of the isocontour layer.")
            changed = changed or _

            imgui.next_column()
            _, self.iso_tolerance[i] = imgui.input_float(
                f"##tol_{i}",
                self.iso_tolerance[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The tolerance of the isocontour layer.")
            changed = changed or _

            imgui.next_column()
            _, self.iso_layers_alpha[i] = imgui.input_float(
                f"##alpha_{i}",
                self.iso_layers_alpha[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The opacity of the isocontour layer.")
            changed = changed or _

            imgui.next_column()
            if imgui.button(f"X##remove_{i}"):
                self._remove_layer(i)
                i -= 1
                _ = True
            changed = changed or _
            imgui.next_column()
            i += 1
        imgui.columns(1)

        return changed

    def _remove_layer(self, layer_id):
        self.iso_layers.pop(layer_id)
        self.iso_layers_alpha.pop(layer_id)
        self.iso_tolerance.pop(layer_id)

    @property
    def _iso_layer_array(self):
        iso_vals = np.asarray(self.iso_layers, dtype="float32")
        if self.iso_log:
            iso_vals = 10**iso_vals
        return iso_vals

    def _get_sanitized_iso_layers(self, normalize=True):
        # returns an array of the isocontour layer values, padded with 0s out
        # to max number of contours (32).
        iso_vals = self._iso_layer_array

        tols = self._get_sanitized_iso_tol()
        iso_min_max = [iso_vals - tols / 2.0, iso_vals + tols / 2.0]

        min_max_outputs = []
        for id in range(2):
            vals = iso_min_max[id]
            if normalize:
                vals = self.data._normalize_by_min_max(vals)

            full_array = np.zeros(32, dtype="float32")
            full_array[: len(self.iso_layers)] = vals.astype("float32")
            min_max_outputs.append(full_array)

        return min_max_outputs

    def _get_sanitized_iso_tol(self):
        tol = np.asarray(self.iso_tolerance)
        if self.iso_log:
            # the tol value is an exponent, convert
            tol = 10**tol

        if self.iso_tol_is_pct:
            # tolerance depends on the layer value
            tol = np.asarray(tol) * 0.01
            iso_vals = self._iso_layer_array
            final_tol = iso_vals * tol
        else:
            final_tol = tol
        return final_tol

    @traitlets.default("transfer_function")
    def _default_transfer_function(self):
        tf = TransferFunctionTexture(data=np.ones((256, 1, 4), dtype="u1") * 255)
        return tf

    def draw(self, scene, program):
        each = self.data.vertex_array.each
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        with self.transfer_function.bind(target=2):
            for tex_ind, tex, bitmap_tex in self.data.viewpoint_iter(scene.camera):
                with tex.bind(target=0):
                    with bitmap_tex.bind(target=1):
                        GL.glDrawArrays(GL.GL_POINTS, tex_ind * each, each)
