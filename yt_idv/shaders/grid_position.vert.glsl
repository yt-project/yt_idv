#version 330
in vec4 model_vertex; // The location of the vertex in model space
out vec4 v_model;
out vec3 v_camera_pos;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;

//// Uniforms
uniform vec3 camera_pos;
uniform mat4 modelview;
uniform mat4 projection;

uniform float near_plane;
uniform float far_plane;

void main()
{
    v_model = model_vertex;
    v_camera_pos = camera_pos;
    inverse_proj = inverse(projection);
    // inverse model-view-matrix
    inverse_mvm = inverse(modelview);
    inverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * model_vertex;

}
