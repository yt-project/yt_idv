from yt import write_bitmap

from .base_context import BaseContext


class OffscreenRenderingContext(BaseContext):
    """Base class for offscreen rendering."""

    def run(self):

        if self.scene is None:
            return
        self.scene.render()
        if self.image_widget is not None:
            self.image_widget.value = write_bitmap(self.scene.image[:, :, :3], None)
            return
        return self.scene.image

    def snap(self, *args, **kwargs):
        if self.scene is None:
            return
        self.scene.render()
        super().snap(*args, **kwargs)
