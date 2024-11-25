import numpy as np
import yt


class BaseContext:
    image_widget = None
    snap_count = 0

    def __init__(self, width, height, **kwargs):
        self.width = width
        self.height = height

    def add_scene(self, ds, field, no_ghost=True):
        """
        add a :class:`SceneGraph` to the current context for the supplied yt data.

        Parameters
        ----------
        ds:
            A yt Dataset or Data Object to use as a source
        field: Union[str, Tuple[str, str]]
            the field to render. can be either a string or a yt field tuple of
            the form ('field_type', 'field').
        no_ghost: bool
            if True, skip ghost zones to improve performance.

        Returns
        -------
        scene: :class:`SceneGraph`

        """
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

    def snap(self, template=r"snap_%04i.png"):
        yt.write_bitmap(self.scene.image[:, :, :3], template % self.snap_count)
        self.snap_count += 1
