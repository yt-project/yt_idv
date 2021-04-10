from math import ceil, floor, log10

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.opengl_support import TransferFunctionTexture
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.shader_objects import component_shaders


class BlockRendering(SceneComponent):
    """
    A class that renders block data.  It may do this in one of several ways,
    including mesh outline.  This allows us to render a single collection of
    blocks multiple times in a single scene and to separate out the memory
    handling from the display.
    """

    name = "block_rendering"
    data = traitlets.Instance(BlockCollection)
    box_width = traitlets.CFloat(0.1)
    sample_factor = traitlets.CFloat(1.0)
    transfer_function = traitlets.Instance(TransferFunctionTexture)
    tf_min = traitlets.CFloat(0.0)
    tf_max = traitlets.CFloat(1.0)
    tf_log = traitlets.Bool(True)
    slice_position = traitlets.Tuple((0.5, 0.5, 0.5), trait=traitlets.CFloat())
    slice_normal = traitlets.Tuple((1.0, 0.0, 0.0), trait=traitlets.CFloat())

    priority = 10

    def render_gui(self, imgui, renderer, scene):
        changed = super().render_gui(imgui, renderer, scene)
        _, sample_factor = imgui.slider_float(
            "Sample Factor", self.sample_factor, 1.0, 20.0
        )
        if _:
            self.sample_factor = sample_factor
        # Now, shaders
        shader_combos = list(sorted(component_shaders[self.name]))
        descriptions = [
            component_shaders[self.name][_]["description"] for _ in shader_combos
        ]
        selected = shader_combos.index(self.render_method)
        _, shader_ind = imgui.listbox("Shader", selected, descriptions)
        if _:
            self.render_method = shader_combos[shader_ind]
        changed = changed or _
        if imgui.button("Add Block Outline"):
            from ..scene_annotations.block_outline import BlockOutline

            block_outline = BlockOutline(data=self.data)
            scene.annotations.append(block_outline)
        if imgui.button("Add Grid Outline"):
            from ..scene_annotations.grid_outlines import GridOutlines
            from ..scene_data.grid_positions import GridPositions

            grids = self.data.data_source.ds.index.grids.tolist()
            gp = GridPositions(grid_list=grids)
            scene.data_objects.append(gp)
            scene.components.append(GridOutlines(data=gp))
        if self.render_method == "transfer_function":
            # Now for the transfer function stuff
            imgui.image_button(
                self.transfer_function.texture_name, 256, 32, frame_padding=0
            )
            imgui.text("Right click and drag to change")
            update = False
            data = self.transfer_function.data.astype("f4") / 255
            for i, c in enumerate("rgba"):
                imgui.plot_lines(
                    f"## {c}",
                    data[:, 0, i].copy(),
                    scale_min=0.0,
                    scale_max=1.0,
                    graph_size=(256, 32),
                )
                if imgui.is_item_hovered() and imgui.is_mouse_dragging(2):
                    update = True
                    dx, dy = renderer.io.mouse_delta
                    dy = -dy
                    mi = imgui.get_item_rect_min()
                    ma = imgui.get_item_rect_max()
                    x, y = renderer.io.mouse_pos
                    x = x - mi.x
                    y = (ma.y - mi.y) - (y - mi.y)
                    xb1 = floor(min(x + dx, x) * data.shape[0] / (ma.x - mi.x))
                    xb2 = ceil(max(x + dx, x) * data.shape[0] / (ma.x - mi.x))
                    yv1 = y / (ma.y - mi.y)
                    yv2 = (y + dy) / (ma.y - mi.y)
                    yv1, yv2 = (max(min(_, 1.0), 0.0) for _ in (yv1, yv2))
                    if dx < 0:
                        yv2, yv1 = yv1, yv2
                        xb1 -= 1
                    elif dx > 0:
                        xb2 += 1
                    xb1 = max(0, xb1)
                    xb2 = min(255, xb2)
                    if renderer.io.key_shift:
                        yv1 = yv2 = 1.0
                    elif renderer.io.key_ctrl:
                        yv1 = yv2 = 0.0
                    data[xb1:xb2, 0, i] = np.mgrid[yv1 : yv2 : (xb2 - xb1) * 1j]
            if update:
                self.transfer_function.data = (data * 255).astype("u1")
        return changed

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

    def _set_uniforms(self, scene, shader_program):
        shader_program._set_uniform("box_width", self.box_width)
        shader_program._set_uniform("sample_factor", self.sample_factor)
        shader_program._set_uniform("ds_tex", 0)
        shader_program._set_uniform("bitmap_tex", 1)
        shader_program._set_uniform("tf_tex", 2)
        shader_program._set_uniform("tf_min", self.tf_min)
        shader_program._set_uniform("tf_max", self.tf_max)
        shader_program._set_uniform("tf_log", float(self.tf_log))
        shader_program._set_uniform("slice_normal", np.array(self.slice_normal))
        shader_program._set_uniform("slice_position", np.array(self.slice_position))

    def _get_sanitized_iso_layers(self):
        # return the sanitized layers

        # pull extrema from `BlockCollection`, these are extrema across all blocks
        data_min = self.data.min_val
        data_max = self.data.max_val
        if self.cmap_log:
            data_min = log10(data_min)
            data_max = log10(data_max)

        # apply the same scaling as in `self.data._load_textures()`
        normalized_isovals = [
            (iso_val - data_min) / (data_max - data_min) for iso_val in self.iso_layers
        ]
        return normalized_isovals
