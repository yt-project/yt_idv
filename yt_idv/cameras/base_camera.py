import contextlib

import numpy as np
import traitlets
import traittypes
from OpenGL import GL

from yt_idv.traitlets_support import YTPositionTrait, ndarray_ro, ndarray_shape


class BaseCamera(traitlets.HasTraits):
    """Camera object used in the Interactive Data Visualization

    Parameters
    ----------

    position : :obj:`!iterable`, or 3 element array in code_length
        The initial position of the camera.
    focus : :obj:`!iterable`, or 3 element array in code_length
        A point in space that the camera is looking at.
    up : :obj:`!iterable`, or 3 element array in code_length
        The 'up' direction for the camera.
    fov : float, optional
        An angle defining field of view in degrees. For an orthographic
        projection, this sets the half-height of the view volume to
        tan(fov/2) * |position - focus|, matching the perspective frustum's
        extent at the focal plane.
    near_plane : float, optional
        The distance to the near plane of the perspective camera.
    far_plane : float, optional
        The distance to the far plane of the perspective camera.
    aspect_ratio: float, optional
        The ratio between the height and the width of the camera's fov.
    projection_type : str, optional
        The projection used to map 3D space onto the image plane, either
        "perspective" (default, rays diverge from the camera position),
        "orthographic" (parallel rays along the view direction) or
        "ray_table" (a ray direction per pixel from ``ray_table``, for
        panoramic and other non-linear lenses).
    ray_table : array, optional
        For the "ray_table" projection, a ``(height, width, 3)`` array of
        camera-space ray directions (the camera looks down -z with +y up), row
        0 at the bottom, zero where a pixel has no ray; see
        ``yt_idv.cameras.ray_table``. Depth is the distance from the ray's
        origin over ``far_plane``.
    ray_origins : array, optional
        For the "ray_table" projection, each ray's origin as an offset from
        ``position`` in camera space, times ``ray_origin_scale``, shaped like
        ``ray_table`` (e.g. per-column eye positions for omnidirectional
        stereo). By default every ray starts at ``position``.
    ray_origin_scale : float, optional
        Scales ``ray_origins`` into model units, so a fixed table can follow
        a changing scale.

    """

    # We have to be careful about some of these, as it's possible in-place
    # operations won't trigger our observation.
    position = YTPositionTrait([0.0, 0.0, 1.0])
    focus = YTPositionTrait([0.0, 0.0, 0.0])
    up = traittypes.Array(np.array([0.0, 0.0, 1.0])).valid(
        ndarray_shape(3), ndarray_ro()
    )
    scroll_delta = traitlets.Float(0.1)
    fov = traitlets.Float(45.0)
    near_plane = traitlets.Float(0.001)
    far_plane = traitlets.Float(20.0)
    aspect_ratio = traitlets.Float(
        1.0
    )  # This was 8.0/6.0 for a long time. I don't know why.
    projection_type = traitlets.CaselessStrEnum(
        ("perspective", "orthographic", "ray_table"), default_value="perspective"
    )
    ray_table = traittypes.Array(None, allow_none=True)
    ray_origins = traittypes.Array(None, allow_none=True)
    ray_origin_scale = traitlets.Float(1.0)

    projection_matrix = traittypes.Array(np.zeros((4, 4))).valid(
        ndarray_shape(4, 4), ndarray_ro()
    )
    view_matrix = traittypes.Array(np.zeros((4, 4))).valid(
        ndarray_shape(4, 4), ndarray_ro()
    )
    orientation = traittypes.Array(np.zeros(4)).valid(ndarray_shape(4), ndarray_ro())

    held = traitlets.Bool(False)

    @contextlib.contextmanager
    def hold_traits(self, func):
        """Suppress per-trait matrix rebuilds inside the block, then call func once."""
        if self.held:
            yield
            return
        self.held = True
        try:
            yield
        finally:
            self.held = False
        func()

    @traitlets.default("up")
    def _default_up(self):
        return np.array([0.0, 1.0, 0.0])

    @traitlets.observe(
        "position", "fov", "near_plane", "far_plane", "aspect_ratio", "projection_type"
    )
    def compute_matrices(self, change=None):
        """Rebuild the projection matrix when a trait that feeds it changes."""
        if self.held:
            return
        self._compute_matrices()

    def _compute_matrices(self):
        pass

    def update_matrices(self):
        """Rebuild the view matrix from position, focus and up, then the projection.

        Call this after setting position, focus or up directly. The orientation
        quaternion is re-derived from the new view matrix.
        """
        pass

    def _update_matrices(self):
        self.update_matrices()

    def set_orientation(self, orientation):
        """Set the orientation quaternion and re-derive position, up and the view.

        The camera keeps its focus and its distance from the focus; position and
        up are rotated to match the new orientation.
        """
        pass

    def update_orientation(self, start_x, start_y, end_x, end_y):
        """Change camera orientation matrix using delta of mouse's cursor position

        Parameters
        ----------

        start_x : float
            initial cursor position in x direction
        start_y : float
            initial cursor position in y direction
        end_x : float
            final cursor position in x direction
        end_y : float
            final cursor position in y direction

        """
        pass

    def pan(self, dx, dy):
        """Pan the camera by a given amount in normalized device coordinates."""
        pass

    def _set_uniforms(self, scene, shader_program):
        GL.glDepthRange(0.0, 1.0)  # Not the same as near/far plane
        shader_program._set_uniform("projection", self.projection_matrix)
        shader_program._set_uniform("modelview", self.view_matrix)
        shader_program._set_uniform(
            "viewport", np.array(GL.glGetIntegerv(GL.GL_VIEWPORT), dtype="f4")
        )
        shader_program._set_uniform(
            "inv_pmvm", np.linalg.inv(self.projection_matrix @ self.view_matrix)
        )
        shader_program._set_uniform("near_plane", self.near_plane)
        shader_program._set_uniform("far_plane", self.far_plane)
        shader_program._set_uniform("camera_pos", self.position)
        view_dir = np.asarray(self.focus - self.position, dtype="f4")
        view_dir = view_dir / np.linalg.norm(view_dir)
        shader_program._set_uniform("camera_view_dir", view_dir)
        shader_program._set_uniform(
            "projection_type",
            {"perspective": 0, "orthographic": 1, "ray_table": 2}[self.projection_type],
        )
        if self.projection_type == "ray_table":
            use_origins = self.ray_origins is not None
            shader_program._set_uniform("use_ray_origins", float(use_origins))
            shader_program._set_uniform("ray_origin_scale", self.ray_origin_scale)
            spread = self._ray_table_entry()["spread"] * self.ray_origin_scale
            shader_program._set_uniform("ray_origin_spread", spread)

    def _ray_table_entry(self):
        # Textures for the two most recent tables, so the eyes of a stereo
        # pair can alternate without rebuilding them.
        from yt_idv.cameras.ray_table import tile_cones
        from yt_idv.opengl_support import Texture2D

        if self.ray_table is None:
            raise ValueError('projection_type "ray_table" needs a ray_table array')
        cache = self.__dict__.setdefault("_ray_table_cache", [])
        for entry in cache:
            if entry["rays"] is self.ray_table and entry["origins"] is self.ray_origins:
                return entry

        def texture(array):
            # Texture2D takes (x, y, channels) arrays
            data = np.ascontiguousarray(np.asarray(array, dtype="f4").swapaxes(0, 1))
            return Texture2D(data=data)

        entry = {
            "rays": self.ray_table,
            "origins": self.ray_origins,
            "textures": [texture(self.ray_table), texture(tile_cones(self.ray_table))],
            "spread": 0.0,
        }
        if self.ray_origins is not None:
            entry["textures"].append(texture(self.ray_origins))
            entry["spread"] = float(np.linalg.norm(self.ray_origins, axis=-1).max())
        cache.insert(0, entry)
        for old in cache[2:]:
            for tex in old["textures"]:
                tex.release()
        del cache[2:]
        return entry

    @contextlib.contextmanager
    def bind_ray_table(self, ray_target, tile_target, origin_target):
        """Bind the ray table, its tile cones and its origins, if this camera uses them."""
        if self.projection_type != "ray_table":
            yield
            return
        textures = self._ray_table_entry()["textures"]
        with contextlib.ExitStack() as stack:
            for tex, target in zip(
                textures, (ray_target, tile_target, origin_target), strict=False
            ):
                stack.enter_context(tex.bind(target))
            yield

    def dict(self):
        # array attributes
        array_attrs = [
            "position",
            "focus",
            "up",
            "orientation",
        ]
        cdict = {ky: getattr(self, ky).tolist() for ky in array_attrs}

        attrs = [
            "fov",
            "near_plane",
            "far_plane",
            "aspect_ratio",
            "projection_type",
        ]
        for ky in attrs:
            cdict[ky] = getattr(self, ky)

        return cdict

    def update(
        self,
        position=None,
        focus=None,
        up=None,
        fov=None,
        near_plane=None,
        far_plane=None,
        aspect_ratio=None,
        projection_type=None,
    ):
        """Set several traits at once, then rebuild the view and projection.

        Traits left as None are untouched. The view matrix is rebuilt from
        position, focus and up and the orientation quaternion is re-derived
        from it (see update_matrices). To set the orientation directly, use
        set_orientation instead.
        """
        values = {
            "position": position,
            "focus": focus,
            "up": up,
            "fov": fov,
            "near_plane": near_plane,
            "far_plane": far_plane,
            "aspect_ratio": aspect_ratio,
            "projection_type": projection_type,
        }
        with self.hold_traits(self.update_matrices):
            for name, val in values.items():
                if val is not None:
                    setattr(self, name, val)

    def update_from_dict(self, cdict):
        """Restore the camera from a snapshot produced by dict().

        The orientation entry is dropped: it is derived from position, focus
        and up, and update re-derives it.
        """
        cdict = {ky: val for ky, val in cdict.items() if ky != "orientation"}
        self.update(**cdict)
