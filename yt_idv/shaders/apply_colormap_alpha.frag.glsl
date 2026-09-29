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
   // color.a is left as cm_tex's own alpha at this position

   gl_FragDepth = texture(db_tex, UV).r;
}
