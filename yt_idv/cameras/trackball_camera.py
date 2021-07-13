import numpy as np
import traitlets
from yt.utilities.math_utils import (
    get_lookat_matrix,
    get_perspective_matrix,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
)

from yt_idv.cameras.base_camera import BaseCamera
from yt_idv.utilities import update_orientation


class TrackballCamera(BaseCamera):
    """

    This class implements a basic "Trackball" or "Arcball" camera control system
    that allows for unconstrained 3D rotations without suffering from Gimbal lock.
    Following Ken Shoemake's original C implementation (Graphics Gems IV, III.1)
    we project mouse movements onto the unit sphere and use quaternions to
    represent the corresponding rotation.

    See also:
    https://en.wikibooks.org/wiki/OpenGL_Programming/Modern_OpenGL_Tutorial_Arcball

    """

    @property
    def proj_func(self):
        return get_perspective_matrix

    @traitlets.default("orientation")
    def _orientation_default(self):
        rotation_matrix = self.view_matrix[0:3, 0:3]
        return rotation_matrix_to_quaternion(rotation_matrix)

    @traitlets.default("view_matrix")
    def _default_view_matrix(self):
        return get_lookat_matrix(self.position, self.focus, self.up)

    def _map_to_surface(self, mouse_x, mouse_y):
        # right now this just maps to the surface of the unit sphere
        x, y = mouse_x, mouse_y
        mag = np.sqrt(x * x + y * y)
        if mag > 1.0:
            x /= mag
            y /= mag
            z = 0.0
        else:
            z = np.sqrt(1.0 - mag ** 2)
        return np.array([x, -y, z])

    def update_orientation(self, start_x, start_y, end_x, end_y):
        self.orientation = update_orientation(
            self.orientation, start_x, start_y, end_x, end_y
        )

        rotation_matrix = quaternion_to_rotation_matrix(self.orientation)
        dp = np.linalg.norm(self.position - self.focus) * rotation_matrix[2]
        self.position = dp + self.focus
        self.up = rotation_matrix[1]

        self.view_matrix = get_lookat_matrix(self.position, self.focus, self.up)

        self.projection_matrix = self.proj_func(
            self.fov, self.aspect_ratio, self.near_plane, self.far_plane
        )

    def _update_matrices(self):

        self.view_matrix = get_lookat_matrix(self.position, self.focus, self.up)
        self.orientation = rotation_matrix_to_quaternion(self.view_matrix[0:3, 0:3])

        self.projection_matrix = self.proj_func(
            self.fov, self.aspect_ratio, self.near_plane, self.far_plane
        )

    def move_forward(self, move_amount):
        dpos = (self.focus - self.position) / np.linalg.norm(self.focus - self.position)
        self.offset_position(move_amount * dpos)

    def offset_position(self, dpos=None):
        if dpos is None:
            dpos = np.array([0.0, 0.0, 0.0])
        self.position += dpos
        self.view_matrix = get_lookat_matrix(self.position, self.focus, self.up)

    def _compute_matrices(self):
        pass
