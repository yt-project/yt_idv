import contextlib

import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.traitlets_support import (
    ArrayTrait,
    YTPositionTrait,
    ndarray_ro,
    ndarray_shape,
)


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

    up = ArrayTrait(np.array([0.0, 0.0, 1.0])).valid(ndarray_shape(3), ndarray_ro())
    scroll_delta = traitlets.Float(0.1)
    fov = traitlets.Float(45.0)
    near_plane = traitlets.Float(0.001)
    far_plane = traitlets.Float(20.0)
    aspect_ratio = traitlets.Float(
        1.0
    )  # This was 8.0/6.0 for a long time. I don't know why.

    projection_matrix = ArrayTrait(np.zeros((4, 4))).valid(
        ndarray_shape(4, 4), ndarray_ro()
    )
    view_matrix = ArrayTrait(np.zeros((4, 4))).valid(ndarray_shape(4, 4), ndarray_ro())
    orientation = ArrayTrait(np.zeros(4)).valid(ndarray_shape(4), ndarray_ro())
    held = traitlets.Bool(False)

    @contextlib.contextmanager
    def hold_traits(self, func):
        # for some reason, hold_trait_notifications doesn't seem to work here.
        # So, we use this to block.  We also do not want to pass the
        # notifications once completed.
        if not self.held:
            self.held = True
            func()
            self.held = False
        yield

    @traitlets.default("up")
    def _default_up(self):
        return np.array([0.0, 1.0, 0.0])

    @traitlets.observe(
        "position",
        "focus",
        "up",
        "fov",
        "near_plane",
        "far_plane",
        "aspect_ratio",
        "orientation",
    )
    def compute_matrices(self, change=None):
        """Regenerate all position, view and projection matrices of the camera."""
        with self.hold_traits(self._compute_matrices):
            pass

    def _update_matrices(self):
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

    def update(self, **kwargs):
        with self.hold_traits(self._compute_matrices):
            for ky, val in kwargs.items():
                setattr(self, ky, val)
