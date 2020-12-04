#version 330 core

in vec2 UV;

out vec4 color;

uniform sampler2D fb_tex;
uniform sampler1D cm_tex;
uniform float min_val;
uniform float scale;
uniform float cmap_min;
uniform float cmap_max;
uniform float cmap_log;

void main(){
   color = texture(fb_tex, UV);
}
