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

   // use the incoming alpha (should be 1 for fragment shaders that do not set it explicitly)
   color.a = alpha;

   gl_FragDepth = texture(db_tex, UV).r;
}
