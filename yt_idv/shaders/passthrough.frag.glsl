in vec2 UV;

out vec4 color;

void main(){
   color = texture(fb_tex, UV) * color_factor;
   color.a = 1.0;
   gl_FragDepth = texture(db_tex, UV).r;
}
