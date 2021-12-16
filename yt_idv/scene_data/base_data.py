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

    def _normalize_by_min_max(self, data):
        # linear normalization of data across full data range
        return (data - self.min_val) / self.val_range

    @property
    def val_range(self):
        # the data range (max - min) across all data.

        # note: not using traitlets here because it seemed overkill to
        # observe min_val and max_val
        return self.max_val - self.min_val
