in vec2 UV;

out vec4 color;

void main(){
   color = texture(fb_tex, UV);
   gl_FragDepth = texture(db_tex, UV).r;
}
