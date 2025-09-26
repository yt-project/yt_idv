from math import ceil, floor

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.gui_support import add_popup_help
from yt_idv.opengl_support import TransferFunctionTexture
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.block_collection import BlockCollection, GridCollection
from yt_idv.shader_objects import component_shaders, get_shader_combos


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
    slice_position = traitlets.Tuple((0.5, 0.5, 0.5)).tag(trait=traitlets.CFloat())
    slice_normal = traitlets.Tuple((1.0, 0.0, 0.0)).tag(trait=traitlets.CFloat())

    priority = 10

    def render_gui(self, imgui, renderer, scene):
        changed = super().render_gui(imgui, renderer, scene)

        _, sample_factor = imgui.slider_float(
            "Sample Factor",
            self.sample_factor,
            1.0,
            20.0,
        )
        if _:
            self.sample_factor = sample_factor
        # Now, shaders
        valid_shaders = get_shader_combos(
            self.name, coord_system=self.data._yt_geom_str
        )
        descriptions = [
            component_shaders[self.name][_]["description"] for _ in valid_shaders
        ]
        selected = valid_shaders.index(self.render_method)
        _, shader_ind = imgui.listbox("Shader", selected, descriptions)
        if _:
            self.render_method = valid_shaders[shader_ind]
        changed = changed or _
        if imgui.button("Add Block Outline"):
            if self.data._yt_geom_str == "cartesian":
                from ..scene_annotations.block_outline import BlockOutline

                block_outline = BlockOutline(data=self.data)
                scene.annotations.append(block_outline)
            elif self.data._yt_geom_str == "spherical":
                from ..scene_data.block_collection import _block_collection_outlines

                cc, cc_render = _block_collection_outlines(
                    self.data, outline_type="blocks"
                )
                scene.data_objects.append(cc)
                scene.components.append(cc_render)

        if imgui.button("Add Grid Outline"):
            if self.data._yt_geom_str == "cartesian":
                from ..scene_annotations.grid_outlines import GridOutlines
                from ..scene_data.grid_positions import GridPositions

                gp = GridPositions(grid_list=self.data.intersected_grids)
                scene.data_objects.append(gp)
                scene.components.append(GridOutlines(data=gp))
            elif self.data._yt_geom_str == "spherical":
                from ..scene_data.block_collection import _block_collection_outlines

                cc, cc_render = _block_collection_outlines(
                    self.data, display_name="grid outlines", outline_type="grids"
                )
                scene.data_objects.append(cc)
                scene.components.append(cc_render)

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

        elif self.render_method == "slice":
            imgui.text("Set slicing parameters:")

            _, self.slice_position = imgui.input_float3(
                "Position", *self.slice_position
            )
            changed = changed or _
            _ = add_popup_help(imgui, "The position of a point on the slicing plane.")
            changed = changed or _
            _, self.slice_normal = imgui.input_float3("Normal", *self.slice_normal)
            changed = changed or _
            _ = add_popup_help(imgui, "The normal vector of the slicing plane.")
            changed = changed or _

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
        if self.data._yt_geom_str == "spherical":
            axis_id = self.data._get_ds().coordinates.axis_id
            shader_program._set_uniform("id_theta", axis_id["theta"])
            shader_program._set_uniform("id_r", axis_id["r"])
            shader_program._set_uniform("id_phi", axis_id["phi"])

        shader_program._set_uniform("box_width", self.box_width)
        shader_program._set_uniform("sample_factor", self.sample_factor)
        shader_program._set_uniform("ds_tex", np.array([0, 0, 0, 0, 0, 0]))
        shader_program._set_uniform("bitmap_tex", 1)
        shader_program._set_uniform("tf_tex", 2)
        shader_program._set_uniform("tf_min", self.tf_min)
        shader_program._set_uniform("tf_max", self.tf_max)
        shader_program._set_uniform("tf_log", float(self.tf_log))
        shader_program._set_uniform("slice_normal", np.array(self.slice_normal))
        shader_program._set_uniform("slice_position", np.array(self.slice_position))

    @property
    def _yt_geom_str(self):
        return self.data._yt_geom_str


class GridCollectionRendering(BlockRendering):
    name = "block_rendering"
    data = traitlets.Instance(GridCollection)
