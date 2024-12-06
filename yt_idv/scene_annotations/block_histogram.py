import numpy as np
import traitlets
from OpenGL import GL

from yt_idv.opengl_support import Texture1D
from yt_idv.scene_annotations.base_annotation import SceneAnnotation
from yt_idv.scene_data.block_collection import BlockCollection


class BlockHistogram(SceneAnnotation):
    """
    A class that computes and displays a histogram of block data.
    """

    name = "block_histogram"
    data = traitlets.Instance(BlockCollection)
    output_data = traitlets.Instance(Texture1D)

    bins = traitlets.CInt(64)
    min_val = traitlets.CFloat(0.0)
    max_val = traitlets.CFloat(1.0)

    _recompute = True

    @traitlets.default("output_data")
    def _default_output_data(self):
        return Texture1D(data=np.zeros(self.bins, dtype="u4"), channels="r32ui")

    def _set_uniforms(self, scene, shader_program):
        pass

    def _set_compute_uniforms(self, scene, shader_program):
        shader_program._set_uniform("min_val", self.min_val)
        shader_program._set_uniform("max_val", self.max_val)
        shader_program._set_uniform("bins", self.bins)

    def compute(self, scene, program):
        # We need a place to dump our stuff.
        self.visible = False
        self.output_data.clear()
        total = 0
        with self.output_data.bind_as_image(2):
            for _tex_ind, tex, bitmap_tex in self.data.viewpoint_iter(scene.camera):
                # We now need to bind our textures.  We don't care about positions.
                total += bitmap_tex.data.size
                with tex.bind(target=0):
                    with bitmap_tex.bind(target=1):
                        GL.glUseProgram(program.program)
                        self._set_compute_uniforms(scene, program)
                        # This will need to be carefully chosen based on our
                        # architecture, I guess.  That aspect of running compute
                        # shaders, CUDA, etc, is one of my absolute least favorite
                        # parts.
                        GL.glDispatchCompute(
                            bitmap_tex.data.shape[0],
                            bitmap_tex.data.shape[1],
                            bitmap_tex.data.shape[2],
                        )
                        GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

    def draw(self, scene, program):
        # This will probably need to have somewhere to draw the darn thing.  So
        # we'll need display coordinates, size, etc.
        pass
