import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer
from yt.data_objects.construction_data_containers import YTProj
from yt.data_objects.selection_objects.slices import YTSlice, YTCuttingPlane
from yt_idv.opengl_support import Texture2D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData
from OpenGL import GL

class BasePlane(SceneData):
    """
    base class for a plane.

    """
    name = "image_plane_data"

    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture2D))

    # blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False)
    size = traitlets.CInt(-1)

    # required!
    normal = traitlets.Instance(np.ndarray)
    center = traitlets.Instance(np.ndarray)
    data = traitlets.Instance(np.ndarray)
    width = traitlets.Float()
    height = traitlets.Float()

    # calculated or sterialized:
    plane_normal = None  # sanitized
    plane_pt = None  # sanitized
    east_vec = None   # calculated
    north_vec = None   # calculated
    plane_width = None  # sanitized
    plane_height = None  # sanitized

    def _set_plane(self):

        plane_origin = self.center  # true center point of the plane, will use this to translate
        self.plane_width = self.width  # in-plane width
        self.plane_height = self.height  # in-plane height

        # set the in-plane coordinate vectors, basis_u = east, basis_v = north
        unit_normal = self.normal / np.linalg.norm(self.normal)
        if self.east_vec is None or self.north_vec is None:
            if unit_normal[0] == 0 and unit_normal[1] == 0:
                east_vec = np.array([1., 0., 0.])
                north_vec = np.array([0., 1., 0.])
            elif unit_normal[1] == 0 and unit_normal[2] == 0:
                east_vec = np.array([0., 1., 0.])
                north_vec = np.array([0., 0., 1.])
            elif unit_normal[0] == 0 and unit_normal[2] == 0:
                east_vec = np.array([1., 0., 0.])
                north_vec = np.array([0., 0., 1.])
            else:
                raise ValueError("It looks like your plane is not normal to an axis, please"
                                 " set east_vec and north_vec before calling add_data().")
        else:
            east_vec = self.east_vec
            north_vec = self.north_vec

        # all of these will get set as uniforms for the vertex shader (that
        # happens in scene_components.planes.ImagePlane._set_uniforms when adding
        # data to the scene).
        self.plane_normal = unit_normal.astype("f4")
        self.east_vec = east_vec.astype("f4")  # east
        self.north_vec = north_vec.astype("f4")  # north
        self.plane_pt = plane_origin.astype("f4")

    def add_data(self):

        self._set_plane()
        # our in-plane coordinates. same as texture coordinates
        verts = np.array([
            [1, 0],
            [0, 0],
            [0, 1],
            [1, 1]
        ])

        i = np.array([
            [0, 1, 2],
            [0, 2, 3]
        ])
        i.shape = (i.size, 1)

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=verts.astype("f4"))
        )

        self.vertex_array.indices = i.astype("uint32")
        self.size = i.size
        # OOPS https://learnopengl.com/Advanced-OpenGL/Face-culling
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
        self.the_texture = texture


class PlaneData(BasePlane):
    """
    a 2D plane built from a yt slice, cutting plane or projection
    """
    data_source = traitlets.Instance(YTDataContainer)

    def add_data(self, field, width, frb_dims=(400, 400)):

        # set our image plane data
        frb = self.data_source.to_frb(width, resolution=frb_dims)
        self.data = frb[field]
        dstype = type(self.data_source)
        if dstype == YTSlice:
            normal = np.zeros((3,))
            normal[self.data_source.axis] = 1.
            center = np.zeros((3,))
            center[self.data_source.axis] = self.data_source.coord
        elif dstype == YTCuttingPlane:
            self.north_vec = self.data_source.orienter.north_vector
            normal = self.data_source.orienter.normal_vector
            self.east_vec = np.cross(normal, self.north_vec)
            center = self.data_source.center.value
        elif isinstance(self.data_source, YTProj):
            normal = np.zeros((3,))
            normal[self.data_source.axis] = 1.
            center = np.zeros((3,))
            center[self.data_source.axis] = 1.
        else:
            raise ValueError(f"Unexpected data_source type. data_source must be one of"
                             f" YTSlice or YTproj but found {dstype}.")

        self.center = center
        self.normal = normal
        self.width = frb_dims[0]
        self.height = frb_dims[1]

        super().add_data()


# class MultiPlane(BasePlane)
# for unifying colormap application
