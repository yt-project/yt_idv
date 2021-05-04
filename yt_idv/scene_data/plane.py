import numpy as np
import traitlets
from OpenGL import GL
from unyt import unyt_quantity
from unyt.exceptions import UnitParseError
from yt.data_objects.construction_data_containers import YTProj
from yt.data_objects.data_containers import YTDataContainer
from yt.data_objects.selection_objects.slices import YTCuttingPlane, YTSlice

from yt_idv.opengl_support import Texture2D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class BasePlane(SceneData):
    """
    base class for a rendering a plane in 3d space using a 2d texture.

    While BasePlane can be used to plot arbitrary image data (see
    plane_textures_arbitrary.py and plane_textures_arbitrary_images.py in examples/),
    the child class PlaneData is easier to use if plotting yt slice, cutting or
    projection objects.

    Parameters
    ----------
    normal: ndarray with shape (3,)
        normal vector to the plane in 3d cartesian image coordinates
    center: ndarray with shape (3,)
        the center point within the plane in 3d cartesian image coordinates
    width: float
        the width of our 2d plane (the euclidean distance covered along the
        "east" dimension by our plane)
    height: float
        the height of our 2d plane (the euclidean distance covered along the
        "north" axis by our plane)
    data: 2D ndarray
        the data to sample on the plane.

    Some important attributes
    -------------------------

    north_vec: ndarray with shape (3,)
        the north vector lying within the plane in 3d cartesian image coordinates
    east_vec: ndarray with shape (3,)
        the east vector lying within the plane in 3d cartesian image coordinates.
        (should equal the cross product between plane_normal and north_vec)

    Both of these must be set manually if the normal vector is not aligned with
    the usual cartesian axes.

    """

    name = "image_plane_data"

    # calculated or sterilized:
    plane_normal = None
    # plane_pt = None
    east_vec = None
    north_vec = None

    # shader-related objects
    texture_object = traitlets.Instance(Texture2D)
    texture_id = traitlets.CInt()
    size = traitlets.CInt(-1)

    # required arguments
    normal = traitlets.Instance(np.ndarray, allow_none=False)
    center = traitlets.Instance(np.ndarray, allow_none=False)
    data = traitlets.Instance(np.ndarray, allow_none=False)
    width = traitlets.Float(allow_none=False)
    height = traitlets.Float(allow_none=False)

    _calculate_translation = False

    def _set_transformation(self):
        """
        here we build the transformation matrix that when applied to the in-plane
        coordinates returns the world coordinates.
        """
        # set the in-plane coordinate vectors, basis_u = east, basis_v = north
        unit_normal = self.normal / np.linalg.norm(self.normal)
        if self.east_vec is None or self.north_vec is None:
            if unit_normal[0] == 0 and unit_normal[1] == 0:
                east_vec = np.array([1.0, 0.0, 0.0])
                north_vec = np.array([0.0, 1.0, 0.0])
            elif unit_normal[1] == 0 and unit_normal[2] == 0:
                east_vec = np.array([0.0, 1.0, 0.0])
                north_vec = np.array([0.0, 0.0, 1.0])
            elif unit_normal[0] == 0 and unit_normal[2] == 0:
                east_vec = np.array([1.0, 0.0, 0.0])
                north_vec = np.array([0.0, 0.0, 1.0])
            else:
                raise ValueError(
                    "It looks like your plane is not normal to an axis, please"
                    " set east_vec and north_vec before calling add_data()."
                )
        else:
            east_vec = self.east_vec
            north_vec = self.north_vec

        # total transformation
        #    M * [U, V, 0., 1], where M = T * W * S
        #    S = scale matrix, to scale distance from UV texture coord to in-plane coord
        #    W = projection matrix to go from in-plane coords to cartesian coords
        #        centered at the world origin
        #    T = translation matrix to go from world origin to plane center

        # homogenous scaling matrix from UV texture coords to in-plane coords
        S = np.eye(4)
        S[0, 0] = self.width
        S[1, 1] = self.height

        # homogenous projection matrix from in-plane coords to world at origin
        W = np.eye(4)
        W[0:3, 0] = east_vec
        W[0:3, 1] = north_vec
        W[0:3, 2] = unit_normal

        to_world = np.matmul(W, S)

        # homogenous translation matrix
        T = np.eye(4)
        if self._calculate_translation:
            # aligns the center of the UV coords with the true center for when
            # the image data array center is not the center. alternatively,
            # could adjust the vertex points, but this seems easier.
            current_center = np.matmul(to_world, np.array([0.5, 0.5, 0.0, 1.0]).T)
            T[0:3, 3] = self.center - current_center[0:3]
        else:
            T[0:3, 3] = self.center

        # combined homogenous projection matrix
        self.to_worldview = np.matmul(T, to_world)
        self.to_worldview = self.to_worldview.astype("f4")

    def add_data(self):

        self._set_transformation()
        # our in-plane coordinates. same as texture coordinates
        verts = np.array([[1, 0], [0, 0], [0, 1], [1, 1]])

        i = np.array([[0, 1, 2], [0, 2, 3]])
        i.shape = (i.size, 1)

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=verts.astype("f4"))
        )

        self.vertex_array.indices = i.astype("uint32")
        self.size = i.size
        self.build_textures()

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="simple_slice", each=0)

    def build_textures(self):
        tex_id = GL.glGenTextures(1)
        bitmap = self.data.astype("f4")
        texture = Texture2D(
            texture_name=tex_id, data=bitmap, boundary_x="clamp", boundary_y="clamp"
        )
        self.texture_id = tex_id
        self.texture_object = texture


class PlaneData(BasePlane):
    """
    a 2D plane built from a yt slice, cutting plane or projection.

    Parameters
    ----------
    data_source: YTDataContainer
        Must be a ds.slice, ds.cutting or ds.proj, where ds is a yt dataset.

    To add a projection to an existing volume rendering scene:

    >>> import yt
    >>> import yt_idv
    >>> from yt_idv.scene_components.planes import Plane
    >>> from yt_idv.scene_data.plane import PlaneData

    >>> ds = yt.load_sample("IsolatedGalaxy")

    >>> # add the volume rendering to the scene
    >>> rc = yt_idv.render_context(height=800, width=800, gui=True)
    >>> sg = rc.add_scene(ds, "density", no_ghost=True)

    >>> # calculate and add a projection through the volume to our 3D rendering
    >>> proj = ds.proj("density", 0)
    >>> proj_data = PlaneData(data_source=proj)
    >>> proj_data.add_data("density", 1.0, (400, 400))
    >>> proj_render = Plane(data=proj_data, cmap_log=True)
    >>> rc.scene.data_objects.append(proj_data)
    >>> rc.scene.components.append(proj_render)

    >>> rc.run()
    """

    data_source = traitlets.Instance(YTDataContainer)
    _calculate_translation = True

    def _sanitize_length_var(self, var, return_scalar=True):
        # pulls out the code_length value for var if it is a unyt quantity
        if hasattr(var, "units"):
            try:
                var = var.to("code_length")
            except UnitParseError:
                var = unyt_quantity(
                    var.value, var.units, registry=self.data_source.ds.unit_registry
                )
                var = var.to("code_length")
            var = var / self.data_source.ds.domain_width
            var = var.value
            if return_scalar:
                var = float(var)
        return var

    def add_data(
        self,
        field,
        width=1.0,
        resolution=(400, 400),
        height=None,
        translate=0.0,
        center=None,
    ):
        """
        generates a fixed resolution buffer from the data_source and adds it
        as a plane in 3D space.

        Parameters
        ----------
        field: tuple
            a yt field tuple, ("field_type", "field")
        translate: float in "code_length" or unyt quantity
            moves the plane by this value in the direction normal to the plane.
            useful for controlling where a projection through a 3D volume is
            displayed.

        The remaining parameters all control the fixed resolution buffer (frb)
        generated from the data_source. See yt's documentation on .to_frb() for
        more details.

        width: float in "code_length" or unyt quantity
            the width of the frb
        resolution: (int, int)
            the resolution of the frb
        height: float in "code_length" or unyt quantity
            the height of the frb
        center: None, ndarray in "code_length", or unyt array
            the center of the frb, must lie within the plane of the data_source
            default None.

        """
        # get our image plane data
        frb_kw_args = dict(resolution=resolution)
        for kw, val in [("height", height), ("center", center)]:
            if np.any(val):
                frb_kw_args[kw] = val

        frb = self.data_source.to_frb(width, **frb_kw_args)
        # field_vals = frb[field]
        # if hasattr(field_vals, 'units'):
        #     field_vals = field_vals.value
        self.data = frb[field]
        if np.any(center):
            center = self._sanitize_length_var(center, return_scalar=False)
            self._calculate_translation = True

        def calc_center(axis_coord_val):
            center = np.zeros((3,))
            for ax, dim in enumerate(["x", "y", "z"]):
                if ax == self.data_source.axis:
                    center[ax] = axis_coord_val
                else:
                    val = np.mean(
                        [
                            frb.limits[dim][0].to("code_length").value,
                            frb.limits[dim][1].to("code_length").value,
                        ]
                    )
                    val = val / self.data_source.ds.domain_width[ax]
                    center[ax] = val
            return center

        # store the parameters defining the plane
        dstype = type(self.data_source)
        if dstype == YTSlice:
            normal = np.zeros((3,))
            normal[self.data_source.axis] = 1.0
            if np.any(center) is None:
                center = calc_center(self.data_source.coord)
        elif dstype == YTCuttingPlane:
            self.north_vec = self.data_source.orienter.north_vector
            self.north_vec = self.north_vec / np.linalg.norm(self.north_vec)
            normal = self.data_source.orienter.normal_vector
            normal = normal / np.linalg.norm(normal)  # make sure it's a unit normal
            self.east_vec = np.cross(normal, self.north_vec)
            self._calculate_translation = True
            if np.any(center) is None:
                center = self.data_source.center.value
        elif isinstance(self.data_source, YTProj):
            normal = np.zeros((3,))
            normal[self.data_source.axis] = 1.0
            if np.any(center) is None:
                center = calc_center(1.0)
        else:
            raise ValueError(
                f"Unexpected data_source type. data_source must be one of"
                f" YTSlice or YTproj but found {dstype}."
            )

        if translate != 0:
            center += self._sanitize_length_var(translate) * normal

        self.center = center
        self.normal = normal
        if height is None:
            height = width
        for dimstr, dim in [("width", width), ("height", height)]:
            setattr(self, dimstr, self._sanitize_length_var(dim))

        super().add_data()
