import contextlib
from math import ceil, floor

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.gui_support import add_popup_help
from yt_idv.opengl_support import (
    Texture2D,
    TransferFunctionTexture,
    VertexAttribute,
    bindless_textures_supported,
)
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

    Note that the meaning of ``sample_factor`` depends on the coordinate system
    of the data. For cartesian data, it is the number of samples taken per cell
    width along a ray. For spherical data, the step size along a ray within a
    volume element is

        ds = eta * min(dr, r * dtheta, r * sin(theta) * dphi)

    and ``sample_factor`` stores log10(eta), so that a ``sample_factor`` of 0
    (the default for spherical data) samples at the smallest characteristic
    length of the element and smaller values sample more finely.
    """

    name = "block_rendering"
    data = traitlets.Instance(BlockCollection)
    box_width = traitlets.CFloat(0.1).tag(config=True)
    sample_factor = traitlets.CFloat().tag(config=True)
    transfer_function = traitlets.Instance(TransferFunctionTexture)
    tf_min = traitlets.CFloat(0.0).tag(config=True)
    tf_max = traitlets.CFloat(1.0).tag(config=True)
    tf_log = traitlets.Bool(True).tag(config=True)
    slice_position = traitlets.Tuple((0.5, 0.5, 0.5)).tag(
        trait=traitlets.CFloat(), config=True
    )
    slice_normal = traitlets.Tuple((1.0, 0.0, 0.0)).tag(
        trait=traitlets.CFloat(), config=True
    )
    # External depth clip used in ray_tracing.frag.glsl for truncating ray integration early based on view
    external_depth_texture = traitlets.Instance(
        Texture2D, allow_none=True, default_value=None
    )
    use_external_depth_clip = traitlets.Bool(False)
    # Draw all the blocks with a single call, giving each block its textures
    # through GL_ARB_bindless_texture handles, instead of binding each block's
    # textures and drawing it separately. Defaults to whether the context
    # supports the extension.
    use_bindless_textures = traitlets.Bool()

    priority = 10

    # the bindless draw's per-block texture handles and index buffer; these
    # belong to this component, not to the data's vertex array, so they are
    # neither shared with other components nor saved with the scene
    _data_handles = None
    _bitmap_handles = None
    _handle_attribute_source = None
    _index_buffer = None

    _saved_attributes = SceneComponent._saved_attributes + ("transfer_function",)

    def render_gui(self, imgui, renderer, scene):
        changed = super().render_gui(imgui, renderer, scene)

        if self.data._yt_geom_str == "spherical":
            _, sample_factor = imgui.slider_float(
                "log10(Sample Factor)",
                self.sample_factor,
                -1.0,
                1.0,
            )
            if _:
                self.sample_factor = sample_factor
                changed = True
            _ = add_popup_help(
                imgui,
                "log10 of the sampling factor, eta. The step size along a ray "
                "within a spherical volume element is eta times the smallest "
                "of the element's characteristic lengths, dr, r * dtheta and "
                "r * sin(theta) * dphi. Smaller values sample more finely.",
            )
            changed = changed or _
        else:
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
        if self.data._yt_geom_str == "cartesian":
            _, self.data.scale = imgui.checkbox("Scale Positions", self.data.scale)
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

    @traitlets.default("sample_factor")
    def _default_sample_factor(self):
        # in spherical coordinates, sample_factor stores log10 of the sampling
        # factor eta (so the default of 0.0 corresponds to eta of 1), while in
        # cartesian coordinates it is the number of samples per cell width.
        data = self._trait_values.get("data", None)
        if data is not None and data._yt_geom_str == "spherical":
            return 0.0
        return 1.0

    @traitlets.default("transfer_function")
    def _default_transfer_function(self):
        tf = TransferFunctionTexture(data=np.ones((256, 1, 4), dtype="u1") * 255)
        return tf

    @traitlets.default("use_bindless_textures")
    def _default_use_bindless_textures(self):
        return bindless_textures_supported()

    @traitlets.observe("data", "use_bindless_textures")
    def _set_bindless_pp_directive(self, change):
        # observing data too applies the default before the shaders are first
        # compiled, since traitlets doesn't notify observers of a default
        directive = ("BINDLESS_TEXTURES", "")
        current_shader = component_shaders[self.name][self.render_method]
        with self.hold_trait_notifications():
            for shd in ("vertex", "geometry", "fragment"):
                if self.use_bindless_textures:
                    self._program1_pp_defs.add_definition(shd, directive)
                elif directive[0] in dict(self._program1_pp_defs[shd]):
                    self._program1_pp_defs.clear_definition(shd, directive)
                shader = current_shader.get(f"first_{shd}", None)
                if shader is not None:
                    setattr(
                        self, f"{shd}_shader", (shader, self._program1_pp_defs[shd])
                    )

    @property
    def _draw_order_matters(self):
        # Blocks have to be drawn furthest first unless the first pass blends
        # them commutatively (a max, a min, or a plain sum) with no depth
        # test, as max_intensity and projection do.
        shader = self.fragment_shader
        if shader is None:
            return True
        if shader.use_separate_blend or shader.depth_test != GL.GL_ALWAYS:
            return True
        if shader.blend_equation in (GL.GL_MAX, GL.GL_MIN):
            return False
        return not (
            shader.blend_equation == GL.GL_FUNC_ADD
            and tuple(shader.blend_func) == (GL.GL_ONE, GL.GL_ONE)
        )

    def _block_order(self, scene):
        """The block indices in the order to draw them, as a uint32 array."""
        if self._draw_order_matters:
            return self.data.viewpoint_order(scene.camera)
        return np.arange(len(self.data.texture_objects), dtype="uint32")

    def draw(self, scene, program):
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        depth_clip_active = (
            self.use_external_depth_clip and self.external_depth_texture is not None
        )
        depth_ctx = (
            self.external_depth_texture.bind(target=3)
            if depth_clip_active
            else contextlib.nullcontext()
        )
        with self.transfer_function.bind(target=2):
            with depth_ctx:
                if self.use_bindless_textures:
                    self._draw_bindless(scene, program)
                else:
                    self._draw_bound(scene)

    def _draw_bound(self, scene):
        # bind each block's textures and draw it on its own
        data = self.data
        each = data.vertex_array.each
        for vbo_i in self._block_order(scene).tolist():
            tex = data.texture_objects[vbo_i]
            bitmap_tex = data.bitmap_objects[vbo_i]
            with tex.bind(target=0):
                with bitmap_tex.bind(target=1):
                    GL.glDrawArrays(GL.GL_POINTS, vbo_i * each, each)

    def _draw_bindless(self, scene, program):
        # draw every block with one call: each block (a single vertex) gets its
        # texture handles from vertex attributes, and when the order matters an
        # index buffer gives it
        handles = self.data.texture_handles()
        if self._handle_attribute_source is not handles:
            self._handle_attribute_source = handles
            if self._data_handles is None:
                self._data_handles = VertexAttribute(name="in_data_tex", integer=True)
                self._bitmap_handles = VertexAttribute(
                    name="in_bitmap_tex", integer=True
                )
            # each 64-bit handle goes to the shaders as a uvec2
            data_handles, bitmap_handles = handles.view("uint32")
            self._data_handles.data = data_handles.reshape(-1, 2)
            self._bitmap_handles.data = bitmap_handles.reshape(-1, 2)
        with self._data_handles.bind(program), self._bitmap_handles.bind(program):
            if not self._draw_order_matters:
                GL.glDrawArrays(GL.GL_POINTS, 0, handles.shape[1])
                return
            order = self.data.viewpoint_order(scene.camera)
            if self._index_buffer is None:
                self._index_buffer = GL.glGenBuffers(1)
            # the element buffer binding is part of the bound vertex array's
            # state, so it is reset afterwards
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._index_buffer)
            GL.glBufferData(
                GL.GL_ELEMENT_ARRAY_BUFFER, order.nbytes, order, GL.GL_STREAM_DRAW
            )
            GL.glDrawElements(GL.GL_POINTS, order.size, GL.GL_UNSIGNED_INT, None)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)

    def _set_uniforms(self, scene, shader_program):
        if self.data._yt_geom_str == "spherical":
            axis_id = self.data.axis_id
            shader_program._set_uniform("id_theta", axis_id["theta"])
            shader_program._set_uniform("id_r", axis_id["r"])
            shader_program._set_uniform("id_phi", axis_id["phi"])

        shader_program._set_uniform("box_width", self.box_width)
        shader_program._set_uniform("sample_factor", self.sample_factor)
        shader_program._set_uniform("data_tex", 0)
        shader_program._set_uniform("bitmap_tex", 1)
        shader_program._set_uniform("tf_tex", 2)
        shader_program._set_uniform("external_depth_tex", 3)
        shader_program._set_uniform(
            "use_external_depth_clip",
            float(
                self.use_external_depth_clip and self.external_depth_texture is not None
            ),
        )
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

        For ``projection``, values are path integrals along the rays cast by
        the camera. With the default perspective camera the rays diverge, so
        the integrals only approximate a yt projection; setting
        ``camera.projection_type = "orthographic"`` before rendering casts
        parallel rays, making them true parallel-ray path integrals (and
        ``RenderedImagePlane.integrate`` then recovers the total up to
        discretization error).
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
