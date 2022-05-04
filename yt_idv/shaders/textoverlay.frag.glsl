in vec2 UV;

out vec4 color;

void main(){
   float val = texture(fb_tex, UV).r;
   gl_FragDepth = 0.0;
   if(val == 0) discard;
   color = vec4(val);
}
