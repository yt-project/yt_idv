"""
Shader and ShaderProgram wrapper classes for vertex and fragment shaders used
in Interactive Data Visualization
"""

# ----------------------------------------------------------------------------
# Copyright (c) 2016, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

# This is a part of the experimental Interactive Data Visualization

from contextlib import ExitStack, contextmanager

import matplotlib.pyplot as plt
import numpy as np
import traitlets
import traittypes
from OpenGL import GL

# Set up a mapping from numbers to names
from yt.utilities.math_utils import get_scale_matrix, get_translate_matrix

from yt_idv._cmyt_utilities import validate_cmyt_name
from yt_idv.constants import bbox_vertices
from yt_idv.texture_packing import pack

const_types = (
    GL.constant.IntConstant,
    GL.constant.LongConstant,
    GL.constant.FloatConstant,
)

num_to_const = {}
for i in dir(GL):
    if i.startswith("GL_"):
        v = getattr(GL, i)
        if not isinstance(v, const_types):
            continue
        num_to_const[v.real] = v

_coersion_funcs = {
    "FLOAT": float,
    "DOUBLE": float,
    "INT": int,
    "UNSIGNED": int,
    "BOOL": bool,
}

_shapes = {
    "MAT2": (2, 2),
    "MAT3": (3, 3),
    "MAT4": (4, 4),
    "MAT2x3": (2, 3),
    "MAT2x4": (2, 4),
    "MAT3x2": (3, 2),
    "MAT3x4": (3, 4),
    "MAT4x2": (4, 2),
    "MAT4x3": (4, 3),
    "VEC2": (2,),
    "VEC3": (3,),
    "VEC4": (4,),
}

# PyOpenGL has the reverse mapping for this
gl_to_np = {
    "FLOAT": "f",
    "DOUBLE": "d",
    "INT": "i",
    "UNSIGNED": "I",
    "BOOL": "b",
}

np_to_gl = {
    "float32": GL.GL_FLOAT,
    "int32": GL.GL_INT,
    "uint32": GL.GL_UNSIGNED_INT,
    "uint8": GL.GL_UNSIGNED_BYTE,
}

TEX_CHANNELS = {
    "float32": {
        1: (GL.GL_FLOAT, GL.GL_R32F, GL.GL_RED),
        2: (GL.GL_FLOAT, GL.GL_RG32F, GL.GL_RG),
        3: (GL.GL_FLOAT, GL.GL_RGB32F, GL.GL_RGB),
        4: (GL.GL_FLOAT, GL.GL_RGBA32F, GL.GL_RGBA),
    },
    "uint8": {
        1: (GL.GL_UNSIGNED_BYTE, GL.GL_R8, GL.GL_RED),
        2: (GL.GL_UNSIGNED_BYTE, GL.GL_RG8, GL.GL_RG),
        3: (GL.GL_UNSIGNED_BYTE, GL.GL_RGB8, GL.GL_RGB),
        4: (GL.GL_UNSIGNED_BYTE, GL.GL_RGBA8, GL.GL_RGBA),
    },
    "uint32": {
        1: (GL.GL_UNSIGNED_INT, GL.GL_R32UI, GL.GL_RED),
        2: (GL.GL_UNSIGNED_INT, GL.GL_RG32UI, GL.GL_RG),
        3: (GL.GL_UNSIGNED_INT, GL.GL_RGB32UI, GL.GL_RGB),
        4: (GL.GL_UNSIGNED_INT, GL.GL_RGBA32UI, GL.GL_RGBA),
    },
}


def coerce_uniform_type(val, gl_type):
    # gl_type here must be in const_types
    if not isinstance(gl_type, const_types):
        gl_type = num_to_const[gl_type]
    # Now we can get down to business!
    spec = gl_type.name.split("_")[1:]  # Strip out the GL_
    # We know what to do with:
    #   FLOAT DOUBLE INT UNSIGNED BOOL
    # We can ignore:
    #    SAMPLER IMAGE
    if "SAMPLER" in spec or "IMAGE" in spec:
        # Do nothing to these, and let PyOpenGL handle it
        return val
    if len(spec) == 1 or spec == ["UNSIGNED", "INT"]:
        return _coersion_funcs[spec[0]](val)
    # We need to figure out if it's a matrix, a vector, etc.
    shape = _shapes[spec[-1]]
    dtype = gl_to_np[spec[0]]
    val = np.asanyarray(val, dtype=dtype)
    val.shape = shape
    return val


class TextureBoundary(traitlets.TraitType):
    default_value = GL.GL_CLAMP_TO_EDGE
    info_text = "A boundary type of mirror, clamp, or repeat"

    def validate(self, obj, value):
        if isinstance(value, str):
            try:
                return {
                    "clamp": GL.GL_CLAMP_TO_EDGE,
                    "mirror": GL.GL_MIRRORED_REPEAT,
                    "repeat": GL.GL_REPEAT,
                }[value.lower()]
            except KeyError:
                self.error(obj, value)
        elif value in (GL.GL_CLAMP_TO_EDGE, GL.GL_MIRRORED_REPEAT, GL.GL_REPEAT):
            return value
        self.error(obj, value)


class GLValue(traitlets.TraitType):
    default_value = GL.GL_NONE
    info_text = "An OpenGL constant."

    def validate(self, obj, value):
        # This will convert lower to upper and spaces to _ and also preprend
        # GL_ if needed.
        if isinstance(value, str):
            if not value.startswith("GL"):
                value = f"GL_{value}"
            value = getattr(GL, value.upper().replace(" ", "_"), None)
            if value is None:
                self.error(obj, value)
        return value


TEX_TARGETS = {i: getattr(GL, f"GL_TEXTURE{i}") for i in range(10)}


def _for_gpu(arr):
    # Float64 data (e.g. from a scene saved at full precision) is kept as it is
    # on the CPU side, and cast down for OpenGL, which takes float32.
    if arr.dtype == np.float64:
        return arr.astype("float32")
    return arr


class Texture(traitlets.HasTraits):
    texture_name = traitlets.CInt(-1)
    data = traittypes.Array(None, allow_none=True)
    channels = GLValue("r32f")
    min_filter = GLValue("linear")
    mag_filter = GLValue("linear")

    @traitlets.default("texture_name")
    def _default_texture_name(self):
        return GL.glGenTextures(1)

    @contextmanager
    def bind(self, target=0):
        _ = GL.glActiveTexture(TEX_TARGETS[target])
        _ = GL.glBindTexture(self.dim_enum, self.texture_name)
        yield
        _ = GL.glActiveTexture(TEX_TARGETS[target])
        GL.glBindTexture(self.dim_enum, 0)

    def release(self):
        if self.trait_has_value("texture_name") and self.texture_name != -1:
            GL.glDeleteTextures(1, [self.texture_name])
            self.texture_name = -1


class Texture1D(Texture):
    boundary_x = TextureBoundary()
    dims = 1
    dim_enum = GLValue("texture 1d")

    @traitlets.observe("data")
    def _set_data(self, change):
        with self.bind():
            data = change["new"]
            if len(data.shape) == 2:
                channels = data.shape[-1]
            else:
                channels = 1
            dx = data.shape[0]
            gl_type, type1, type2 = TEX_CHANNELS[data.dtype.name][channels]
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            if not isinstance(change["old"], np.ndarray):
                GL.glTexStorage1D(GL.GL_TEXTURE_1D, 6, type1, dx)
            GL.glTexSubImage1D(GL.GL_TEXTURE_1D, 0, 0, dx, type2, gl_type, data)
            GL.glTexParameterf(GL.GL_TEXTURE_1D, GL.GL_TEXTURE_WRAP_S, self.boundary_x)
            GL.glTexParameteri(
                GL.GL_TEXTURE_1D, GL.GL_TEXTURE_MIN_FILTER, self.min_filter
            )
            GL.glTexParameteri(
                GL.GL_TEXTURE_1D, GL.GL_TEXTURE_MAG_FILTER, self.mag_filter
            )
            GL.glGenerateMipmap(GL.GL_TEXTURE_1D)


class ColormapTexture(Texture1D):
    colormap_name = traitlets.CUnicode()

    def __init__(self, *args, **kwargs):
        # Override...
        kwargs["boundary_x"] = "clamp"
        super().__init__(*args, **kwargs)

    @traitlets.validate("colormap_name")
    def _validate_name(self, proposal):
        try:
            plt.get_cmap(validate_cmyt_name(proposal["value"]))
        except ValueError:
            raise traitlets.TraitError(
                "Colormap name needs to be known by matplotlib"
            ) from None
        return proposal["value"]

    @traitlets.observe("colormap_name")
    def _observe_colormap_name(self, change):
        cmap = plt.get_cmap(validate_cmyt_name(change["new"]))
        cmap_vals = np.array(cmap(np.linspace(0, 1, 256)), dtype="f4")
        self.data = cmap_vals


class Texture2D(Texture):
    boundary_x = TextureBoundary()
    boundary_y = TextureBoundary()
    dims = 2
    channels = 1
    dim_enum = GLValue("texture 2d")

    @traitlets.observe("data")
    def _set_data(self, change):
        with self.bind():
            data = change["new"]
            if len(data.shape) == 3:
                channels = data.shape[-1]
            else:
                channels = 1
            self.channels = channels
            dx, dy = data.shape[:2]
            gl_type, type1, type2 = TEX_CHANNELS[data.dtype.name][channels]
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            if not isinstance(change["old"], np.ndarray):
                GL.glTexStorage2D(GL.GL_TEXTURE_2D, 2, type1, dx, dy)
            GL.glTexSubImage2D(
                GL.GL_TEXTURE_2D, 0, 0, 0, dx, dy, type2, gl_type, data.swapaxes(0, 1)
            )
            GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, self.boundary_x)
            GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, self.boundary_y)
            GL.glTexParameteri(
                GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, self.min_filter
            )
            GL.glTexParameteri(
                GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, self.mag_filter
            )
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)


class TransferFunctionTexture(Texture2D):
    def __init__(self, *args, **kwargs):
        kwargs["boundary_x"] = "clamp"
        kwargs["boundary_y"] = "clamp"
        super().__init__(*args, **kwargs)


class DepthBuffer(Texture2D):
    def create_texture(self, w, h):
        with self.bind():
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0,
                GL.GL_DEPTH_COMPONENT24,
                w,
                h,
                0,
                GL.GL_DEPTH_COMPONENT,
                GL.GL_FLOAT,
                None,
            )
            GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, self.boundary_x)
            GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, self.boundary_y)
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)


class Texture3D(Texture):
    boundary_x = TextureBoundary()
    boundary_y = TextureBoundary()
    boundary_z = TextureBoundary()
    dims = 3
    dim_enum = GLValue("texture 3d")

    @traitlets.observe("data")
    def _set_data(self, change):
        with self.bind():
            data = _for_gpu(change["new"])
            if len(data.shape) == 4:
                channels = data.shape[-1]
            else:
                channels = 1
            dx, dy, dz = data.shape[:3]
            gl_type, type1, type2 = TEX_CHANNELS[data.dtype.name][channels]
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            if not isinstance(change["old"], np.ndarray):
                # the sampling state is only set when the storage is allocated
                GL.glTexParameterf(
                    GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_S, self.boundary_x
                )
                GL.glTexParameterf(
                    GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_T, self.boundary_y
                )
                GL.glTexParameterf(
                    GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_R, self.boundary_z
                )
                GL.glTexParameteri(
                    GL.GL_TEXTURE_3D, GL.GL_TEXTURE_MIN_FILTER, self.min_filter
                )
                GL.glTexParameteri(
                    GL.GL_TEXTURE_3D, GL.GL_TEXTURE_MAG_FILTER, self.mag_filter
                )
                GL.glTexStorage3D(GL.GL_TEXTURE_3D, 1, type1, dx, dy, dz)
            GL.glTexSubImage3D(
                GL.GL_TEXTURE_3D, 0, 0, 0, 0, dx, dy, dz, type2, gl_type, data.T
            )
            GL.glGenerateMipmap(GL.GL_TEXTURE_3D)

    def allocate(self, dims, dtype="float32", channels=1):
        """Allocate uninitialized storage of shape dims, without uploading data.

        Like _set_data, the sampling state is set along with the storage.
        """
        dx, dy, dz = (int(_) for _ in dims)
        _, type1, _ = TEX_CHANNELS[np.dtype(dtype).name][channels]
        with self.bind():
            GL.glTexParameterf(GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_S, self.boundary_x)
            GL.glTexParameterf(GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_T, self.boundary_y)
            GL.glTexParameterf(GL.GL_TEXTURE_3D, GL.GL_TEXTURE_WRAP_R, self.boundary_z)
            GL.glTexParameteri(
                GL.GL_TEXTURE_3D, GL.GL_TEXTURE_MIN_FILTER, self.min_filter
            )
            GL.glTexParameteri(
                GL.GL_TEXTURE_3D, GL.GL_TEXTURE_MAG_FILTER, self.mag_filter
            )
            GL.glTexStorage3D(GL.GL_TEXTURE_3D, 1, type1, dx, dy, dz)

    def set_subdata(self, offset, data):
        """Upload data into the region of the texture starting at offset."""
        channels = data.shape[-1] if data.ndim == 4 else 1
        dx, dy, dz = data.shape[:3]
        ox, oy, oz = (int(_) for _ in offset)
        gl_type, _, type2 = TEX_CHANNELS[data.dtype.name][channels]
        with self.bind():
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            GL.glTexSubImage3D(
                GL.GL_TEXTURE_3D, 0, ox, oy, oz, dx, dy, dz, type2, gl_type, data.T
            )


class VertexAttribute(traitlets.HasTraits):
    name = traitlets.CUnicode("attr")
    id = traitlets.CInt(-1)
    data = traittypes.Array(None, allow_none=True)
    each = traitlets.CInt(-1)
    opengl_type = traitlets.CInt(GL.GL_FLOAT)
    divisor = traitlets.CInt(0)
    # integer attributes (declared ivec/uvec in the shader) keep their values
    # exactly; otherwise they are converted to float
    integer = traitlets.Bool(False)

    @traitlets.default("id")
    def _id_default(self):
        return GL.glGenBuffers(1)

    @contextmanager
    def bind(self, program=None):
        loc = -1
        if program is not None:
            loc = GL.glGetAttribLocation(program.program, self.name)
            if loc >= 0:
                GL.glVertexAttribDivisor(loc, self.divisor)
                _ = GL.glEnableVertexAttribArray(loc)
        _ = GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.id)
        if loc >= 0:
            if self.integer:
                GL.glVertexAttribIPointer(loc, self.each, self.opengl_type, 0, None)
            else:
                GL.glVertexAttribPointer(
                    loc, self.each, self.opengl_type, False, 0, None
                )
        yield
        if loc >= 0:
            GL.glDisableVertexAttribArray(loc)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @traitlets.observe("data")
    def _set_data(self, change):
        arr = _for_gpu(change["new"])
        self.each = arr.shape[-1]
        self.opengl_type = np_to_gl[arr.dtype.name]
        with self.bind():
            GL.glBufferData(GL.GL_ARRAY_BUFFER, arr.nbytes, arr, GL.GL_STATIC_DRAW)

    def release(self):
        if self.trait_has_value("id") and self.id != -1:
            GL.glDeleteBuffers(1, [self.id])
            self.id = -1


class VertexArray(traitlets.HasTraits):
    name = traitlets.CUnicode("vertex")
    id = traitlets.CInt(-1)
    indices = traittypes.Array(None, allow_none=True)
    index_id = traitlets.CInt(-1)
    attributes = traitlets.List(trait=traitlets.Instance(VertexAttribute))
    each = traitlets.CInt(-1)

    @traitlets.default("id")
    def _id_default(self):
        return GL.glGenVertexArrays(1)

    def __getitem__(self, key):
        for att in self.attributes:
            if att.name == key:
                return att
        raise KeyError(key)

    def keys(self):
        return [_.name for _ in self.attributes]

    def release(self):
        for att in self.attributes:
            att.release()
        if self.index_id != -1:
            GL.glDeleteBuffers(1, [self.index_id])
            self.index_id = -1
        if self.trait_has_value("id") and self.id != -1:
            GL.glDeleteVertexArrays(1, [self.id])
            self.id = -1

    @contextmanager
    def bind(self, program=None):
        GL.glBindVertexArray(self.id)
        if self.index_id != -1:
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.index_id)
        # We only bind the attributes if we have a program too
        if program is None:
            attrs = []
        else:
            attrs = self.attributes
        with ExitStack() as stack:
            _ = [stack.enter_context(_.bind(program)) for _ in attrs]
            yield
        if self.index_id != -1:
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

    @traitlets.observe("indices")
    def _set_indices(self, change):
        arr = change["new"]
        if self.index_id != -1:
            GL.glDeleteBuffers(1, self.index_id)
            self.index_id = -1  # In case of error
        self.index_id = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.index_id)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, arr.nbytes, arr, GL.GL_STATIC_DRAW)


class TextureAtlas(traitlets.HasTraits):
    """
    Many 3D blocks packed into a single Texture3D.

    The atlas is laid out once, when it is created, from the blocks' sizes and
    padding; to change the layout, create a new atlas. No axis of it is larger
    than GL_MAX_3D_TEXTURE_SIZE, and if the blocks don't fit, creating it
    raises a ValueError. Block i's interior starts at offsets[i], and padding
    texels on every side of it (filled by __setitem__ with the block's edge
    values) keep linear interpolation from reading a neighboring block.

    If a vertex array is given, the offsets and sizes are added to it as the
    integer vertex attributes offset_attribute_name and size_attribute_name
    (ivec3s in the shaders), one per block, so the sizes have to be given in
    the vertex array's block order.
    """

    sizes = traittypes.Array(None, allow_none=True, read_only=True)
    padding = traitlets.CInt(0, read_only=True)
    offsets = traittypes.Array(None, allow_none=True, read_only=True)
    dims = traittypes.Array(None, allow_none=True, read_only=True)
    dtype = traitlets.CUnicode("float32")
    channels = traitlets.CInt(1)
    min_filter = GLValue("linear")
    mag_filter = GLValue("linear")
    texture = traitlets.Instance(Texture3D, allow_none=True)
    vertex_array = traitlets.Instance(VertexArray, allow_none=True)
    offset_attribute_name = traitlets.CUnicode("in_texture_offset")
    size_attribute_name = traitlets.CUnicode("in_texture_size")

    def __init__(self, sizes, padding=0, **kwargs):
        super().__init__(**kwargs)
        sizes = np.asarray(sizes, dtype="int64").reshape(-1, 3)
        max_dim = GL.glGetInteger(GL.GL_MAX_3D_TEXTURE_SIZE)
        offsets, dims = pack(sizes, padding=padding, max_dim=max_dim)
        self.set_trait("sizes", sizes)
        self.set_trait("padding", padding)
        self.set_trait("offsets", offsets)
        self.set_trait("dims", np.asarray(dims, dtype="int64"))
        self.texture = Texture3D(
            min_filter=self.min_filter,
            mag_filter=self.mag_filter,
            boundary_x="clamp",
            boundary_y="clamp",
            boundary_z="clamp",
        )
        self.texture.allocate(self.dims, self.dtype, self.channels)
        self._set_attributes()

    def __len__(self):
        return self.sizes.shape[0]

    def __setitem__(self, index, data):
        """Upload block index's data, padded with its edge values."""
        data = np.asarray(data, dtype=self.dtype)
        if data.shape[:3] != tuple(self.sizes[index]):
            raise ValueError(
                f"Block {index} has size {tuple(self.sizes[index])}, "
                f"got data of shape {data.shape}"
            )
        if self.padding > 0:
            pad = [(self.padding, self.padding)] * 3 + [(0, 0)] * (data.ndim - 3)
            data = np.pad(data, pad, mode="edge")
        self.texture.set_subdata(self.offsets[index] - self.padding, data)

    @traitlets.observe("vertex_array")
    def _observe_vertex_array(self, change):
        self._set_attributes()

    def _set_attributes(self):
        if self.vertex_array is None or self.offsets is None:
            return
        for name, arr in (
            (self.offset_attribute_name, self.offsets),
            (self.size_attribute_name, self.sizes),
        ):
            data = arr.astype("int32")
            if name in self.vertex_array.keys():
                attr = self.vertex_array[name]
                attr.integer = True
                attr.data = data
            else:
                self.vertex_array.attributes.append(
                    VertexAttribute(name=name, data=data, integer=True)
                )

    @contextmanager
    def bind(self, target=0):
        with self.texture.bind(target=target):
            yield

    def release(self):
        # the offset and size attributes belong to the vertex array, which
        # releases them
        if self.texture is not None:
            self.texture.release()
            self.texture = None


def _pixels_by_row(arr, width, height):
    # glReadPixels fills its result one row of width pixels at a time, but
    # PyOpenGL shapes it (width, height, ...), so it is reshaped to be indexed
    # [y, x, ...]. (The two agree only for square viewports.)
    arr = np.asarray(arr)
    return arr.reshape((height, width) + arr.shape[2:])


class Framebuffer(traitlets.HasTraits):
    fb_id = traitlets.CInt(-1)
    rb_id = traitlets.CInt(-1)
    fb_tex = traitlets.Instance(Texture2D)
    db_tex = traitlets.Instance(DepthBuffer)
    viewport = traitlets.Tuple(
        traitlets.CInt(), traitlets.CInt(), traitlets.CInt(), traitlets.CInt()
    )
    initialized = traitlets.Bool(False)

    @property
    def data(self):
        """The color buffer, indexed [y, x, channel] with row 0 at the bottom."""
        origin_x, origin_y, width, height = self.viewport
        with self.bind(clear=False):
            arr = GL.glReadPixels(0, 0, width, height, GL.GL_RGBA, GL.GL_FLOAT)
        return _pixels_by_row(arr, width, height)

    @property
    def depth_data(self):
        """The depth buffer, indexed [y, x] with row 0 at the bottom."""
        origin_x, origin_y, width, height = self.viewport
        with self.bind(clear=False):
            arr = GL.glReadPixels(
                0, 0, width, height, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT
            )
        return _pixels_by_row(arr, width, height)

    @traitlets.default("viewport")
    def _viewport_default(self):
        # origin_x, origin_y, width, height
        return tuple(GL.glGetIntegerv(GL.GL_VIEWPORT))

    @traitlets.observe("viewport")
    def _viewport_changed(self, change):
        # we just need to disable the initialized value here
        self.initialized = False

    @traitlets.default("fb_id")
    def _fb_id_default(self):
        return GL.glGenFramebuffers(1)

    @traitlets.default("rb_id")
    def _rb_id_default(self):
        return GL.glGenRenderbuffers(1)

    @traitlets.default("fb_tex")
    def _fb_tex_default(self):
        data = np.zeros((self.viewport[2], self.viewport[3], 4), "f4")
        return Texture2D(data=data, boundary_x="repeat", boundary_y="repeat")

    @traitlets.default("db_tex")
    def _db_tex_default(self):
        db = DepthBuffer(boundary_x="repeat", boundary_y="repeat")
        db.create_texture(self.viewport[2], self.viewport[3])
        return db

    @contextmanager
    def bind(self, clear=True):
        self.viewport = tuple(GL.glGetIntegerv(GL.GL_VIEWPORT))
        if not self.initialized:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fb_id)
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.rb_id)
            GL.glRenderbufferStorage(
                GL.GL_RENDERBUFFER,
                GL.GL_DEPTH_COMPONENT32F,
                self.viewport[2],
                self.viewport[3],
            )
            GL.glFramebufferRenderbuffer(
                GL.GL_FRAMEBUFFER,
                GL.GL_DEPTH_ATTACHMENT,
                GL.GL_RENDERBUFFER,
                self.rb_id,
            )

            GL.glFramebufferTexture2D(
                GL.GL_FRAMEBUFFER,
                GL.GL_COLOR_ATTACHMENT0,
                GL.GL_TEXTURE_2D,
                self.fb_tex.texture_name,
                0,  # mipmap level, normally 0
            )
            GL.glFramebufferTexture2D(
                GL.GL_FRAMEBUFFER,
                GL.GL_DEPTH_ATTACHMENT,
                GL.GL_TEXTURE_2D,
                self.db_tex.texture_name,
                0,  # mipmap level, normally 0
            )
            status = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
            if status != GL.GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError
            self.initialized = True
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fb_id)
        if clear:
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        yield
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    @contextmanager
    def input_bind(self, fb_target=0, db_target=1):
        with self.fb_tex.bind(fb_target):
            with self.db_tex.bind(db_target):
                yield

    def release(self):
        if self.trait_has_value("fb_tex"):
            self.fb_tex.release()
        if self.trait_has_value("db_tex"):
            self.db_tex.release()
        if self.trait_has_value("fb_id") and self.fb_id != -1:
            GL.glDeleteFramebuffers(1, [self.fb_id])
            self.fb_id = -1
        if self.trait_has_value("rb_id") and self.rb_id != -1:
            GL.glDeleteRenderbuffers(1, [self.rb_id])
            self.rb_id = -1
        self.initialized = False


class Texture3DIterator(traitlets.HasTraits):
    items = traitlets.Any()

    def __iter__(self, target=0):
        tex_target = TEX_TARGETS[target]
        for i, t in self.items:
            GL.glActiveTexture(tex_target)
            GL.glBindTexture(GL.GL_TEXTURE_3D, t.texture_name)
            yield i
        GL.glActiveTexture(tex_target)
        GL.glBindTexture(GL.GL_TEXTURE_3D, 0)


def compute_box_geometry(left_edge, right_edge):
    move = get_translate_matrix(*left_edge)
    width = right_edge - left_edge
    scale = get_scale_matrix(*width)

    transformed_box = bbox_vertices.dot(scale.T).dot(move.T).astype("float32")
    return transformed_box
