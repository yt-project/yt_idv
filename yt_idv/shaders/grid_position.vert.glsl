#version 330
in vec4 model_vertex; // The location of the vertex in model space
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;
flat out vec4 vv_model;
flat out vec3 vv_camera_pos;
flat out mat4 vinverse_proj;
flat out mat4 vinverse_mvm;
flat out mat4 vinverse_pmvm;
flat out vec3 vdx;
flat out vec3 vleft_edge;
flat out vec3 vright_edge;

//// Uniforms
uniform vec3 camera_pos;
uniform mat4 modelview;
uniform mat4 projection;

uniform float near_plane;
uniform float far_plane;

void main()
{
    vv_model = model_vertex;
    vv_camera_pos = camera_pos;
    vinverse_proj = inverse(projection);
    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * model_vertex;
    vdx = vec3(in_dx);
    vleft_edge = vec3(in_left_edge);
    vright_edge = vec3(in_right_edge);

}
