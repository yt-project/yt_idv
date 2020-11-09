import numpy as np
import yt


class BaseContext:
    image_widget = None

    def __init__(self, width, height, **kwargs):
        self.width = width
        self.height = height

    def add_scene(self, ds, field, no_ghost=True):
        from ..scene_graph import SceneGraph

        self.scene = SceneGraph.from_ds(ds, field, no_ghost=no_ghost)
        return self.scene

    def add_image(self, width=None, height=None):
        import ipywidgets

        width = width or self.width
        height = height or self.height
        # We will initialize it
        if self.scene is not None:
            value = yt.write_bitmap(self.scene.image[:, :, :3], None)
        else:
            value = yt.write_bitmap(np.zeros((width, height, 3)), None)
        self.image_widget = ipywidgets.Image(width=width, height=height, value=value)
        return self.image_widget
