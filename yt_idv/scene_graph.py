import contextlib

import traitlets
from OpenGL import GL
from yt.data_objects.static_output import Dataset

from yt_idv.cameras.base_camera import BaseCamera
from yt_idv.cameras.trackball_camera import TrackballCamera
from yt_idv.opengl_support import Framebuffer
from yt_idv.scene_annotations.base_annotation import SceneAnnotation
from yt_idv.scene_annotations.box import BoxAnnotation
from yt_idv.scene_annotations.text import TextAnnotation
from yt_idv.scene_components.base_component import SceneComponent
from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_data.base_data import SceneData
from yt_idv.scene_data.block_collection import BlockCollection
from yt_idv.scene_data.box import BoxData
from yt_idv.scene_data.text_characters import TextCharacters


class SceneGraph(traitlets.HasTraits):
    components = traitlets.List(
        trait=traitlets.Instance(SceneComponent), default_value=[]
    )
    annotations = traitlets.List(
        trait=traitlets.Instance(SceneAnnotation), default_value=[]
    )
    data_objects = traitlets.List(trait=traitlets.Instance(SceneData), default_value=[])
    camera = traitlets.Instance(BaseCamera)
    ds = traitlets.Instance(Dataset)
    fb = traitlets.Instance(Framebuffer, allow_none=True)
    input_captured_mouse = traitlets.Bool(False)
    input_captured_keyboard = traitlets.Bool(False)

    def add_volume(self, data_source, field_name, no_ghost=False):
        self.data_objects.append(BlockCollection(data_source=data_source))
        self.data_objects[-1].add_data(field_name, no_ghost=no_ghost)
        self.components.append(BlockRendering(data=self.data_objects[-1]))
        return self.components[-1]  # Only the rendering object

    def add_text(self, **kwargs):
        if "data" not in kwargs:
            if not any(_.name == "text_overlay" for _ in self.data_objects):
                self.data_objects.append(TextCharacters())
                self.data_objects[-1].build_textures()
            kwargs["data"] = next(
                (_ for _ in self.data_objects if _.name == "text_overlay")
            )
        self.annotations.append(TextAnnotation(**kwargs))
        return self.annotations[-1]

    def add_box(self, left_edge, right_edge):
        data = BoxData(left_edge=left_edge, right_edge=right_edge)
        self.data_objects.append(data)
        self.annotations.append(BoxAnnotation(data=data))

    def __iter__(self):
        elements = self.components + self.annotations
        for element in sorted(elements, key=lambda a: a.priority):
            yield element

    def render(self):
        origin_x, origin_y, width, height = GL.glGetIntegerv(GL.GL_VIEWPORT)
        with self.bind_buffer():
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        for element in self:
            # If we need to clear the region, we need to use the scissor test
            db = element.display_bounds
            new_origin_x = origin_x + width * db[0]
            new_origin_y = origin_y + height * db[2]
            new_width = (db[1] - db[0]) * width
            new_height = (db[3] - db[2]) * height
            GL.glViewport(
                int(new_origin_x), int(new_origin_y), int(new_width), int(new_height)
            )
            if element.clear_region:
                GL.glEnable(GL.GL_SCISSOR_TEST)
                GL.glScissor(
                    int(new_origin_x),
                    int(new_origin_y),
                    int(new_width),
                    int(new_height),
                )
                GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                GL.glDisable(GL.GL_SCISSOR_TEST)
            element.run_program(self)
        GL.glViewport(origin_x, origin_y, width, height)

    @contextlib.contextmanager
    def bind_buffer(self):
        if self.fb is not None:
            with self.fb.bind(clear=False):
                yield
        else:
            yield

    @property
    def image(self):
        if self.fb is not None:
            arr = self.fb.data[::-1, :, :]
            arr.swapaxes(0, 1)
            return arr
        _, _, width, height = GL.glGetIntegerv(GL.GL_VIEWPORT)
        arr = GL.glReadPixels(0, 0, width, height, GL.GL_RGBA, GL.GL_FLOAT)[::-1, :, :]
        arr.swapaxes(0, 1)
        return arr

    @property
    def depth(self):
        if self.fb is not None:
            arr = self.fb.depth_data[::-1, :]
            arr.swapaxes(0, 1)
            return arr
        _, _, width, height = GL.glGetIntegerv(GL.GL_VIEWPORT)
        arr = GL.glReadPixels(0, 0, width, height, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT)[
            ::-1, :
        ]
        arr.swapaxes(0, 1)
        return arr

    @staticmethod
    def from_ds(ds, field, no_ghost=True):
        # Here we make a bunch of guesses.  Nothing too complex -- only two
        # arguments: dataset and field.  If you supply a rendering context,
        # great.  If not, we'll make one.
        if isinstance(ds, Dataset):
            data_source = ds.all_data()
        else:
            ds, data_source = ds.ds, ds
        center = ds.domain_center
        pos = center + 1.5 * ds.domain_width
        near_plane = 3.0 * ds.index.get_smallest_dx().min().d

        c = TrackballCamera(position=pos, focus=center, near_plane=near_plane)

        scene = SceneGraph(camera=c)
        scene.add_volume(data_source, field, no_ghost=no_ghost)
        return scene
