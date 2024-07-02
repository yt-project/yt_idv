import numpy as np
import traitlets

from yt_idv.gui_support import add_popup_help


class Isolayers(traitlets.HasTraits):
    iso_tol_is_pct = traitlets.Bool(True)  # if True, the tolerance is a fraction
    iso_log = traitlets.Bool(True)  # if True, iso values are base 10 exponents
    iso_tolerance = traitlets.List()  # the tolerance for finding isocontours
    iso_layers = traitlets.List()  # the target values for isocontours
    iso_layers_alpha = traitlets.List()  # the transparency of isocontours

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

    @traitlets.observe("render_method")
    def _add_initial_isolayer(self, change):
        # this adds an initial isocontour entry when the render method
        # switches to isocontours and if there are no layers yet.
        if change["new"] == "isocontours" and len(self.iso_layers) == 0:
            val = (self.data.min_val + self.data.max_val) / 2.0
            if self.iso_log:
                val = np.log10(val)
            self.iso_layers.append(val)
            self.iso_tolerance.append(0.0)
            self.iso_layers_alpha.append(1.0)

    def _set_iso_uniforms(self, p):
        # these could be handled better by watching traits.
        p._set_uniform("iso_num_layers", int(len(self.iso_layers)))
        isolayervals = self._get_sanitized_iso_layers()
        p._set_uniform("iso_layers_min", isolayervals[0])
        p._set_uniform("iso_layers_max", isolayervals[1])
        avals = np.zeros((32,), dtype="float32")
        avals[: len(self.iso_layers)] = np.array(self.iso_layers_alpha)
        p._set_uniform("iso_alphas", avals)

    def _render_isolayer_inputs(self, imgui) -> bool:
        changed = False
        if imgui.tree_node("Isocontours"):
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
            _ = self._construct_isolayer_table(imgui)
            changed = changed or _
            imgui.tree_pop()
        return changed

    def _construct_isolayer_table(self, imgui) -> bool:
        imgui.columns(4, "iso_layers_cols", False)

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
            _, self.iso_tolerance[i] = imgui.input_float(
                f"tol {i}",
                self.iso_tolerance[i],
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            _ = add_popup_help(imgui, "The tolerance of the isocontour layer.")
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
