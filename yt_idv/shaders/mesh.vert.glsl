#version 330 core

in vec4 model_vertex;
in float vertex_data;
out float fragment_data;
uniform mat4 model
void main()
{
    gl_Position = modelview * projection * model_vertex;
    fragmentData = vertexData;
}
