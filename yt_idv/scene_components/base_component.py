import traitlets
from OpenGL import GL

from yt_idv.constants import FULLSCREEN_QUAD
from yt_idv.opengl_support import (
    ColormapTexture,
    Framebuffer,
    VertexArray,
    VertexAttribute,
)
from yt_idv.scene_data.base_data import SceneData
from yt_idv.shader_objects import (
    ShaderProgram,
    ShaderTrait,
    component_shaders,
    default_shader_combos,
)


class SceneComponent(traitlets.HasTraits):
    data = traitlets.Instance(SceneData)
    base_quad = traitlets.Instance(SceneData)
    name = "undefined"
    priority = traitlets.CInt(0)
    visible = traitlets.Bool(True)
    display_bounds = traitlets.Tuple(
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        traitlets.CFloat(),
        default_value=(0.0, 1.0, 0.0, 1.0),
    )
    clear_region = traitlets.Bool(False)

    render_method = traitlets.Unicode(allow_none=True)
    fragment_shader = ShaderTrait(allow_none=True).tag(shader_type="fragment")
    geometry_shader = ShaderTrait(allow_none=True).tag(shader_type="geometry")
    vertex_shader = ShaderTrait(allow_none=True).tag(shader_type="vertex")
    fb = traitlets.Instance(Framebuffer)
    colormap_fragment = ShaderTrait(allow_none=True).tag(shader_type="fragment")
    colormap_vertex = ShaderTrait(allow_none=True).tag(shader_type="vertex")
    colormap = traitlets.Instance(ColormapTexture)
    _program1 = traitlets.Instance(ShaderProgram, allow_none=True)
    _program2 = traitlets.Instance(ShaderProgram, allow_none=True)
    _program1_invalid = True
    _program2_invalid = True

    # These attributes are
    cmap_min = traitlets.CFloat(None, allow_none=True)
    cmap_max = traitlets.CFloat(None, allow_none=True)
    cmap_log = traitlets.Bool(True)
    scale = traitlets.CFloat(1.0)

    @traitlets.observe("display_bounds")
    def _change_display_bounds(self, change):
        # We need to update the framebuffer if the width or height has changed
        # Same thing is true if the total pixel size has changed, but that is
        # not doable from in here.
        if change["old"] == traitlets.Undefined:
            return
        old_width = change["old"][1] - change["old"][0]
        old_height = change["old"][3] - change["old"][2]
        new_width = change["new"][1] - change["new"][0]
        new_height = change["new"][3] - change["new"][2]
        if old_width != new_width or old_height != new_height:
            self.fb = Framebuffer()

    def render_gui(self, imgui, renderer):
        changed, self.visible = imgui.checkbox("Visible", self.visible)
        return changed

    @traitlets.default("render_method")
    def _default_render_method(self):
        return default_shader_combos[self.name]

    @traitlets.observe("render_method")
    def _change_render_method(self, change):
        new_combo = component_shaders[self.name][change["new"]]
        with self.hold_trait_notifications():
            self.vertex_shader = new_combo["first_vertex"]
            self.fragment_shader = new_combo["first_fragment"]
            self.geometry_shader = new_combo.get("first_geometry", None)
            self.colormap_vertex = new_combo["second_vertex"]
            self.colormap_fragment = new_combo["second_fragment"]

    @traitlets.default("fb")
    def _fb_default(self):
        return Framebuffer()

    @traitlets.observe("fragment_shader")
    def _change_fragment(self, change):
        # Even if old/new are the same
        self._program1_invalid = True

    @traitlets.observe("vertex_shader")
    def _change_vertex(self, change):
        # Even if old/new are the same
        self._program1_invalid = True

    @traitlets.observe("geometry_shader")
    def _change_geometry(self, change):
        self._program1_invalid = True

    @traitlets.observe("colormap_vertex")
    def _change_colormap_vertex(self, change):
        # Even if old/new are the same
        self._program2_invalid = True

    @traitlets.observe("colormap_fragment")
    def _change_colormap_fragment(self, change):
        # Even if old/new are the same
        self._program2_invalid = True

    @traitlets.default("colormap")
    def _default_colormap(self):
        cm = ColormapTexture()
        cm.colormap_name = "arbre"
        return cm

    @traitlets.default("vertex_shader")
    def _vertex_shader_default(self):
        return component_shaders[self.name][self.render_method]["first_vertex"]

    @traitlets.default("fragment_shader")
    def _fragment_shader_default(self):
        return component_shaders[self.name][self.render_method]["first_fragment"]

    @traitlets.default("geometry_shader")
    def _geometry_shader_default(self):
        _ = component_shaders[self.name][self.render_method]
        return _.get("first_geometry", None)

    @traitlets.default("colormap_vertex")
    def _colormap_vertex_default(self):
        return component_shaders[self.name][self.render_method]["second_vertex"]

    @traitlets.default("colormap_fragment")
    def _colormap_fragment_default(self):
        return component_shaders[self.name][self.render_method]["second_fragment"]

    @traitlets.default("base_quad")
    def _default_base_quad(self):
        bq = SceneData(
            name="fullscreen_quad", vertex_array=VertexArray(name="tri", each=6),
        )
        fq = FULLSCREEN_QUAD.reshape((6, 3), order="C")
        bq.vertex_array.attributes.append(
            VertexAttribute(name="vertexPosition_modelspace", data=fq)
        )
        return bq

    @property
    def program1(self):
        if self._program1_invalid:
            if self._program1 is not None:
                self._program1.delete_program()
            self._fragment_shader_default()
            self._program1 = ShaderProgram(
                self.vertex_shader, self.fragment_shader, self.geometry_shader
            )
            self._program1_invalid = False
        return self._program1

    @property
    def program2(self):
        if self._program2_invalid:
            if self._program2 is not None:
                self._program2.delete_program()
            # The vertex shader will always be the same.
            # The fragment shader will change based on whether we are
            # colormapping or not.
            self._program2 = ShaderProgram(self.colormap_vertex, self.colormap_fragment)
            self._program2_invalid = False
        return self._program2

    def run_program(self, scene):
        # Store this info, because we need to render into a framebuffer that is the
        # right size.
        x0, y0, w, h = GL.glGetIntegerv(GL.GL_VIEWPORT)
        GL.glViewport(0, 0, w, h)
        if not self.visible:
            return
        with self.fb.bind(True):
            with self.program1.enable() as p:
                self._set_uniforms(scene, p)
                with self.data.vertex_array.bind(p):
                    self.draw(scene, p)
        if self.cmap_min is None or self.cmap_max is None:
            data = self.fb.data
            data = data[data[:, :, 3] > 0][:, 0]
            if self.cmap_min is None and data.size > 0:
                self.cmap_min = cmap_min = data.min()
            if self.cmap_max is None and data.size > 0:
                self.cmap_max = cmap_max = data.max()
            if data.size == 0:
                cmap_min = 0.0
                cmap_max = 1.0
        else:
            cmap_min = float(self.cmap_min)
            cmap_max = float(self.cmap_max)
        with self.colormap.bind(0):
            with self.fb.input_bind(1, 2):
                with self.program2.enable() as p2:
                    with scene.bind_buffer():
                        p2._set_uniform("cmap", 0)
                        p2._set_uniform("fb_tex", 1)
                        p2._set_uniform("db_tex", 2)
                        # Note that we use cmap_min/cmap_max, not
                        # self.cmap_min/self.cmap_max.
                        p2._set_uniform("cmap_min", cmap_min)
                        p2._set_uniform("cmap_max", cmap_max)
                        p2._set_uniform("cmap_log", float(self.cmap_log))
                        with self.base_quad.vertex_array.bind(p2):
                            # Now we do our viewport globally, not just within
                            # the framebuffer
                            GL.glViewport(x0, y0, w, h)
                            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

    def draw(self, scene, program):
        raise NotImplementedError
