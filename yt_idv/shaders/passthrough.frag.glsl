#version 330 core

in vec2 UV;

out vec4 color;
uniform sampler2D fb_tex;
uniform sampler2D db_tex;

void main(){
   color = texture(fb_tex, UV);
   color.a = 1.0;
   gl_FragDepth = texture(db_tex, UV).r;
}
