#version 330 core

in vec4 model_vertex;
in float vertex_data;
out float fragment_data;
uniform mat4 modelview;
uniform mat4 projection;
void main()
{
    gl_Position = projection * modelview * model_vertex;
    fragment_data = vertex_data;
}
