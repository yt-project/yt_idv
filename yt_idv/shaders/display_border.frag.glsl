in vec2 UV;

out vec4 color;

void main(){
   color = texture(fb_tex, UV);
   color.a = 1.0;
   vec2 d = abs(UV - vec2(0.5));
   if(0.5 - max(d.x, d.y) < draw_boundary) {
      color = vec4(boundary_color);
   }
   gl_FragDepth = texture(db_tex, UV).r;
}
