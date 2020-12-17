in vec2 UV;

out vec4 color;

void main(){
   color = texture(fb_tex, UV);
}
