in vec4 model_vertex; // The location of the vertex in model space
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;
out vec4 v_model;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out vec3 dx;
flat out vec3 left_edge;
flat out vec3 right_edge;
flat out ivec3 texture_offset;

void main()
{
    vec4 grid_width = vec4(in_right_edge - in_left_edge, 0.0);
    v_model = vec4(in_left_edge, 1.0) + grid_width * model_vertex;
    inverse_proj = inverse(projection);
    // inverse model-view-matrix
    inverse_mvm = inverse(modelview);
    inverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * v_model;
    dx = vec3(in_dx);
    left_edge = vec3(in_left_edge);
    right_edge = vec3(in_right_edge);
    texture_offset = ivec3(0, 0, gl_InstanceID);
}