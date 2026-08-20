"""Tests for the imgui overlay helpers in `yt_idv.simple_gui`."""

import types

import pytest


class _FakeWindow:
    """Stand-in for a pyglet window reporting the sizes we care about."""

    def __init__(self, size, framebuffer_size, pixel_ratio):
        self._size = size
        self._framebuffer_size = framebuffer_size
        self._pixel_ratio = pixel_ratio

    def get_size(self):
        return self._size

    def get_framebuffer_size(self):
        return self._framebuffer_size

    def get_pixel_ratio(self):
        return self._pixel_ratio


def _apply_fix(window):
    from yt_idv.simple_gui import SimpleGUI

    gui = types.SimpleNamespace(
        renderer=types.SimpleNamespace(io=types.SimpleNamespace(font_global_scale=1.0))
    )
    SimpleGUI._fix_hidpi_scaling(gui, window)
    return gui.renderer.io


@pytest.mark.parametrize(
    "size,framebuffer_size,pixel_ratio,expected_fb_scale,expected_font_scale",
    [
        # standard display: everything is 1:1
        ((800, 600), (800, 600), 1.0, (1.0, 1.0), 1.0),
        # macOS + pyglet >= 2.1: sizes are already in physical pixels, but
        # the pixel ratio is still 2, so imgui must not scale again.
        ((1600, 1200), (1600, 1200), 2.0, (1.0, 1.0), 2.0),
        # pyglet <= 2.0, where get_pixel_ratio() is framebuffer/window: the
        # scale imgui already computes is the one we compute, so this is a
        # no-op and the font must not be touched.
        ((800, 600), (1600, 1200), 2.0, (2.0, 2.0), 1.0),
    ],
)
def test_hidpi_scaling(
    size, framebuffer_size, pixel_ratio, expected_fb_scale, expected_font_scale
):
    io = _apply_fix(_FakeWindow(size, framebuffer_size, pixel_ratio))
    assert io.display_size == size
    assert io.display_fb_scale == expected_fb_scale
    assert io.font_global_scale == expected_font_scale


def test_hidpi_scaling_ignores_unrealized_window():
    """A zero-sized window must not raise; imgui's own guess is left alone."""
    io = _apply_fix(_FakeWindow((0, 0), (0, 0), 1.0))
    assert not hasattr(io, "display_size")
    assert io.font_global_scale == 1.0
