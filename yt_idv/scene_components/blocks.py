from math import ceil, floor

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.gui_support import add_popup_help
from yt_idv.opengl_support import TransferFunctionTexture
from yt_idv.rendered_image_plane import RenderedImagePlane, image_plane_extent
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_data.block_collection import BlockCollection
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
            axis_id = self.data.data_source.ds.coordinates.axis_id
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

    def rendered_image_plane(self):
        """
        Extract the rendered image as data values in physical units.

        Requires ``store_first_pass_fb`` to have been set to True before the
        scene was rendered, so that the values written by the first rendering
        pass are available (the second pass replaces them with colors).

        Returns
        -------
        RenderedImagePlane
            Holds the image as a unyt array along with the physical extent of
            the view. Units depend on the render method: ``slice`` and
            ``max_intensity`` are in the units of the rendered field, while
            ``projection`` is in field units times a length.

        Notes
        -----
        Values are the absolute value of the rendered field, sampled from the
        vertex-centered data used to build the 3D textures, so they can fall
        slightly outside the range of the cell-centered field (particularly with
        ``no_ghost=True``).
        """
        if self.first_pass_fb_rgba is None:
            raise RuntimeError(
                "No stored framebuffer data: set store_first_pass_fb to True "
                "and render the scene before calling rendered_image_plane."
            )

        supported = ("slice", "max_intensity", "projection")
        if self.render_method not in supported:
            raise NotImplementedError(
                f"rendered_image_plane is not implemented for the "
                f"{self.render_method} render method (supported: {supported})."
            )

        block_collection = self.data
        ds = block_collection.data_source.ds
        field_units = block_collection.field_units or ""
        length_unit = block_collection.internal_length_unit

        fb_data = self.first_pass_fb_rgba
        # values accumulate in the R channel; a nonzero alpha marks the pixels
        # that a ray actually sampled data in.
        values = fb_data[:, :, 0].astype("float64")
        sampled = fb_data[:, :, 3] > 0

        path_length = None
        if self.render_method == "projection":
            # the shader integrates the normalized values,
            #    I = sum_i n_i ds_i,  where  n_i = (|d_i| - min) / (max - min)
            # so recovering the integral of the field values requires the total
            # path length, L = sum_i ds_i, which the shader accumulates in G:
            #    sum_i |d_i| ds_i = I * (max - min) + min * L
            path_length = fb_data[:, :, 1].astype("float64")
            if block_collection._textures_are_normalized:
                values = (
                    values * block_collection.val_range
                    + block_collection.min_val * path_length
                )
            # rays that missed the data integrate to zero, which is correct, so
            # no masking is applied here.
            data = ds.arr(values, field_units) * length_unit
            path_length = path_length * length_unit
        else:
            # slice and max_intensity both write a single normalized value
            if block_collection._textures_are_normalized:
                values = block_collection._denormalize_by_min_max(values)
            values[~sampled] = np.nan
            data = ds.arr(values, field_units)

        camera_state = self._first_pass_camera
        extent, right, up = image_plane_extent(
            camera_state["projection_matrix"],
            camera_state["view_matrix"],
            camera_state["focus"],
        )

        return RenderedImagePlane(
            data=data,
            extent=extent * length_unit,
            center=camera_state["focus"] * length_unit,
            right=right,
            up=up,
            path_length=path_length,
        )
