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
        An angle defining field of view in degrees.
    near_plane : float, optional
        The distance to the near plane of the perspective camera.
    far_plane : float, optional
        The distance to the far plane of the perspective camera.
    aspect_ratio: float, optional
        The ratio between the height and the width of the camera's fov.

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

    @traitlets.observe("position", "fov", "near_plane", "far_plane", "aspect_ratio")
    def compute_matrices(self, change=None):
        """Rebuild the projection matrix when a trait that feeds it changes.
        """
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
