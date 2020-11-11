import numpy as np
import pyglet
from yt import write_bitmap

from yt_idv.simple_gui import SimpleGUI

from .base_context import BaseContext


class PygletRenderingContext(pyglet.window.Window, BaseContext):
    """Basic rendering context for IDV using GLFW3, that handles the main window even loop

    Parameters
    ----------
    width : int, optional
        The width of the Interactive Data Visualization window.  For
        performance reasons it is recommended to use values that are natural
        powers of 2.
    height : int, optional
        The height of the Interactive Data Visualization window.  For
        performance reasons it is recommended to use values that are natural
        powers of 2.
    title : str, optional
        The title of the Interactive Data Visualization window.
    position : tuple of ints, optional
        What position should the window be moved to? (Upper left)  If not
        specified, default to center.
    """

    _do_update = True

    def __init__(
        self,
        width=1024,
        height=1024,
        title="vol_render",
        position=None,
        visible=True,
        gui=True,
        scene=None,
    ):
        self.offscreen = not visible
        config = pyglet.gl.Config(
            major_version=3, minor_version=3, forward_compat=True, double_buffer=True
        )
        super(PygletRenderingContext, self).__init__(
            width, height, config=config, visible=visible, caption=title
        )
        if position is None:
            self.center_window()
        else:
            # self.set_position(*position)
            self.set_location(*position)

        if gui:
            gui = SimpleGUI(self)
        self.gui = gui
        self.scene = scene

    def on_draw(self):
        self.switch_to()
        if self._do_update and self.scene:
            self._do_update = False
            self.clear()
            if self.scene is not None:
                # This should check if the scene is actually dirty, and only
                # redraw the FB if it's not; this might need another flag
                self.scene.render()
                if self.image_widget is not None:
                    self.image_widget.value = write_bitmap(
                        self.scene.image[:, :, :3], None
                    )
        if self.gui:
            self.switch_to()
            self.gui.render(self.scene)

    def set_position(self, xpos, ypos):
        if xpos < 0 or ypos < 0:
            raise RuntimeError
        max_width = self.screen.width
        max_height = self.screen.height
        win_width, win_height = self.width, self.height
        if 0 < xpos < 1:
            # We're being fed relative coords.  We offset these for the window
            # center.
            xpos = max(xpos * max_width - 0.5 * win_width, 0)
        if 0 < ypos < 1:
            # We're being fed relative coords.  We offset these for the window
            # center.
            ypos = max(ypos * max_height - 0.5 * win_height, 0)
        print("Setting position", xpos, ypos)
        self.set_location(int(xpos), int(ypos))

    def center_window(self):
        self.set_position(0.5, 0.5)

    def on_mouse_press(self, x, y, button, modifiers):
        self._do_update = True

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.gui and self.gui.mouse_event_handled:
            self._do_update = True
            return
        start_x = -1.0 + 2.0 * x / self.width
        end_x = -1.0 + 2.0 * (x - dx) / self.width
        start_y = -1.0 + 2.0 * y / self.height
        end_y = -1.0 + 2.0 * (y + dy) / self.height

        self.scene.camera.update_orientation(start_x, start_y, end_x, end_y)
        self._do_update = True

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # captures mouse scrolling as zoom in/out
        if self.gui and self.gui.mouse_event_handled:
            self._do_update = True
            return

        camera = self.scene.camera  # current camera
        dpos = (
            0.1
            * (camera.position - camera.focus)
            / np.linalg.norm(camera.position - camera.focus)
        )

        # wheel scroll comes in the scroll_y parameter with a value +/- 1
        # +1 when scrolling "down", -1 when scrolling "up", so
        # flip it so scrolling "down" zooms out:
        zoom_inout = -1 * scroll_y
        self.scene.camera.offset_position(zoom_inout * dpos)
        self._do_update = True

    def on_key_press(self, symbol, modifiers):
        # skeleton for capturing key presses!

        # potential navigation keys
        if symbol in [pyglet.window.key.LEFT, pyglet.window.key.A]:
            pass
        if symbol in [pyglet.window.key.RIGHT, pyglet.window.key.D]:
            pass
        if symbol in [pyglet.window.key.UP, pyglet.window.key.W]:
            pass
        if symbol in [pyglet.window.key.DOWN, pyglet.window.key.S]:
            pass

    def run(self):
        pyglet.app.run()
