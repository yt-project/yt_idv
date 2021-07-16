import traitlets

from yt_idv.opengl_support import Texture, VertexArray


class SceneData(traitlets.HasTraits):
    """A class that defines a collection of GPU-managed data.

    This class contains the largest common set of features that can be used
    OpenGL rendering: a set of vertices and a set of vertex attributes.  Note
    that this is distinct from the shader, which can be swapped out and
    provided with these items.

    """

    name = traitlets.Unicode()
    vertex_array = traitlets.Instance(VertexArray)
    textures = traitlets.List(trait=traitlets.Instance(Texture))

    min_val = traitlets.CFloat(0.0)
    max_val = traitlets.CFloat(1.0)
