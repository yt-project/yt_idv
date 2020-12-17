in vec2 UV;

out vec4 color;

void main(){
   color = texture(cm_tex, UV.x);
   color.a = 1.0;
}
