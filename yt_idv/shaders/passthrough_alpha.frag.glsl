// Real bug fix (cycles-volume-override): identical to passthrough.frag.glsl
// EXCEPT it does not force `color.a = 1.0`. That override is appropriate
// for passthrough's other callers (opaque outlines/text/line overlays,
// where always-opaque is the intended look), but block_rendering's
// "transfer_function" render_method uses `passthrough` as its own SECOND
// pass -- meaning every genuinely transparent/empty pixel from the first
// pass's real, per-pixel accumulated alpha (transfer_function.frag.glsl's
// own physically-based front-to-back compositing) got forcibly turned
// opaque here, silently discarding it. Confirmed empirically: a scene with
// `film_transparent`-equivalent background handling came back with alpha
// exactly 1.0 everywhere a block was rasterized, RGB correctly (0,0,0) at
// genuinely-empty pixels -- i.e. transparent content rendered as solid
// black instead of see-through. See known_uniforms.inc.glsl-adjacent
// cycles-volume-override docs (`yt_idv_renderer.py`'s module docstring) for
// the full story. Used ONLY for `component_shaders.block_rendering.
// transfer_function`'s `second_fragment` (both cartesian and octree
// variants) -- every other `second_fragment: passthrough` usage
// (outlines, text, line plots, curves) is left pointing at the original,
// unmodified `passthrough.frag.glsl`.
in vec2 UV;

out vec4 color;

void main(){
   color = texture(fb_tex, UV);
   gl_FragDepth = texture(db_tex, UV).r;
}
