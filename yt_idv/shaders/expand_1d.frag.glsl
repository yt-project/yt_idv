#version 330 core

in vec2 UV;

out vec4 color;
uniform sampler1D cm_tex;

void main(){
   color = texture(cm_tex, UV.x);
   color.a = 1.0;
}
