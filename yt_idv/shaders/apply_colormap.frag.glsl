in vec2 UV;

out vec4 color;

void main(){
   float scaled = 0;
   #ifdef USE_DB
   scaled = texture(db_tex, UV).x;
   #else
   scaled = texture(fb_tex, UV).x;
   #endif
   #ifdef COVERAGE_FROM_VALUE
   // single channel first passes have no alpha: undrawn pixels hold the
   // cleared value, 0 for sums or the lowest float for maxima
   float raw = texture(fb_tex, UV).r;
   if (raw == 0.0 || raw < -1e38) discard;
   float alpha = 1.0;
   #else
   float alpha = texture(fb_tex, UV).a;  // the incoming framebuffer alpha
   if (alpha == 0.0) discard;
   #endif
   float cm = cmap_min;
   float cp = cmap_max;

   if (cmap_log > 0.5) {
       scaled = log(scaled);
       cm = log(cm);
       cp = log(cp);
   }
   color = texture(cm_tex, (scaled - cm) / (cp - cm));

   // use the incoming alpha (should be 1 for fragment shaders that do not set it explicitly)
   color.a = alpha;

   gl_FragDepth = texture(db_tex, UV).r;
}
