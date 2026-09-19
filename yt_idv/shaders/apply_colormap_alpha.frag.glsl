// Real feature addition (cycles-volume-override): identical to
// apply_colormap.frag.glsl EXCEPT it does NOT override color.a with the
// incoming framebuffer alpha (which for max_intensity/projection is just a
// binary "was anything found along this ray" flag, not tied to the actual
// selected value at all -- see yt_idv_renderer.py's own docstring for the
// full account). Instead this keeps cm_tex's OWN alpha channel at the
// looked-up position, so a colormap built with a real alpha gradient
// (transparent at the low end, opaque at the high end, or any other shape)
// genuinely controls per-pixel opacity by the max-intensity-selected VALUE
// itself, not just by presence/absence. Background correctness is
// unaffected: the `if (alpha == 0.0) discard;` check below still runs
// first and discards the fragment entirely for pixels where nothing was
// found at all, exactly as in apply_colormap.frag.glsl -- only the ALPHA
// USED FOR SURVIVING FRAGMENTS differs.
in vec2 UV;

out vec4 color;

void main(){
   float scaled = 0;
   #ifdef USE_DB
   scaled = texture(db_tex, UV).x;
   #else
   scaled = texture(fb_tex, UV).x;
   #endif
   float alpha = texture(fb_tex, UV).a;  // the incoming framebuffer alpha
   if (alpha == 0.0) discard;
   float cm = cmap_min;
   float cp = cmap_max;

   if (cmap_log > 0.5) {
       scaled = log(scaled);
       cm = log(cm);
       cp = log(cp);
   }
   color = texture(cm_tex, (scaled - cm) / (cp - cm));
   // color.a is left as cm_tex's own alpha at this position -- the whole
   // point of this shader (see file header).

   gl_FragDepth = texture(db_tex, UV).r;
}
