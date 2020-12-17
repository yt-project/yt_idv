in vec2 UV;

out vec4 color;

void main(){
   float scaled = texture(fb_tex, UV).x;
   float alpha = texture(fb_tex, UV).a;
   if (alpha == 0.0) discard;
   float cm = cmap_min;
   float cp = cmap_max;

   if (cmap_log > 0.5) {
      scaled = log(scaled);
      cm = log(cm);
      cp = log(cp);
   }
   color = texture(cm_tex, (scaled - cm) / (cp - cm));
   gl_FragDepth = texture(db_tex, UV).r;
}
