import math

import imgui
import matplotlib.pyplot as plt
import numpy as np
from imgui.integrations.pyglet import create_renderer
from yt.visualization.image_writer import write_bitmap, write_image

from .opengl_support import Texture2D


class SimpleGUI:
    renderer = None
    callbacks = None
    context = None
    window = None
    draw = False

    def __init__(self, window):
        self.window = window
        self.context = imgui.create_context()
        self.renderer = create_renderer(window)
        self.snapshot_count = 0
        self.snapshot_format = r"snap_{count:04d}.png"
        data = plt.get_cmap("viridis")(np.mgrid[0.0:1.0:256j]).reshape((-1, 1, 4))
        self.data = dict(
            r=data[:, 0, 0].astype("f4"),
            g=data[:, 0, 1].astype("f4"),
            b=data[:, 0, 2].astype("f4"),
            a=data[:, 0, 3].astype("f4"),
        )
        data = (data[:, :, :4] * 255).astype("u1")
        self.colormap = Texture2D(data=data, boundary_x="clamp", boundary_y="clamp")

    def render(self, scene):
        imgui.new_frame()
        changed = False
        if scene is not None:
            imgui.style_colors_classic()
            imgui.begin("Scene")
            imgui.text("Filename Template:")
            _, self.snapshot_format = imgui.input_text("", self.snapshot_format, 256)
            if imgui.button("Save Snapshot"):
                # Call render again, since we're in the middle of overlaying
                # some stuff and we want a clean scene snapshot
                scene.render()
                write_bitmap(
                    scene.image[:, :, :3],
                    self.snapshot_format.format(count=self.snapshot_count),
                )
                self.snapshot_count += 1
            if imgui.tree_node("Debug"):
                if imgui.button("Save Depth"):
                    scene.render()
                    write_image(
                        scene.depth,
                        self.snapshot_format.format(count=self.snapshot_count),
                    )
                    self.snapshot_count += 1
                imgui.tree_pop()
            _ = self.render_camera(scene)
            changed = changed or _
            # imgui.show_style_editor()
            for i, element in enumerate(scene):
                if imgui.tree_node(f"element {i + 1}: {element.display_name}"):
                    changed = changed or element.render_gui(imgui, self.renderer, scene)
                    imgui.tree_pop()
            self.window._do_update = self.window._do_update or changed
            imgui.end()
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def render_camera(self, scene):
        if not imgui.tree_node("Camera"):
            return
        changed = False
        with imgui.begin_group():
            imgui.text("Log of Scroll Delta")
            _, scroll_delta = imgui.slider_float(
                "value", math.log10(scene.camera.scroll_delta), -3.0, 0.0
            )
        if _:
            scene.camera.scroll_delta = 10**scroll_delta
            changed = True
        with scene.camera.hold_trait_notifications():
            for attr in ("position", "up", "focus"):
                arr = getattr(scene.camera, attr)
                imgui.text(f"Camera {attr}")
                _, values = imgui.input_float3(
                    "",
                    arr[0],
                    arr[1],
                    arr[2],
                    flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
                )
                changed = changed or _
                if _:
                    setattr(scene.camera, attr, np.array(values))
            _, values = imgui.input_float2(
                "Camera Planes",
                scene.camera.near_plane,
                scene.camera.far_plane,
                format="%0.6f",
                flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE,
            )
            changed = changed or _
            if _:
                scene.camera.near_plane = values[0]
                scene.camera.far_plane = values[1]
            if imgui.button("Center"):
                scene.camera.position = np.array([0.499, 0.499, 0.499])
                scene.camera.focus = np.array([0.5, 0.5, 0.5])
                changed = True
            imgui.same_line()
            if imgui.button("Outside"):
                scene.camera.position = np.array([1.5, 1.5, 1.5])
                scene.camera.focus = np.array([0.5, 0.5, 0.5])
                changed = True
            imgui.same_line()
            if imgui.button("X Up"):
                scene.camera.position = np.array([0.5, 1.5, 0.5])
                scene.camera.focus = np.array([0.5, 0.5, 0.5])
                scene.camera.up = np.array([1.0, 0.0, 0.0])
                changed = True
            imgui.same_line()
            if imgui.button("Y Up"):
                scene.camera.position = np.array([0.5, 0.5, 1.5])
                scene.camera.focus = np.array([0.5, 0.5, 0.5])
                scene.camera.up = np.array([0.0, 1.0, 0.0])
                changed = True
            imgui.same_line()
            if imgui.button("Z Up"):
                scene.camera.position = np.array([1.5, 0.5, 0.5])
                scene.camera.focus = np.array([0.5, 0.5, 0.5])
                scene.camera.up = np.array([0.0, 0.0, 1.0])
                changed = True
        if changed:
            scene.camera._update_matrices()
        imgui.tree_pop()
        return changed

    @property
    def mouse_event_handled(self):
        return self.renderer.io.want_capture_mouse

    @property
    def keyboard_event_handled(self):
        return self.renderer.io.want_capture_keyboard
