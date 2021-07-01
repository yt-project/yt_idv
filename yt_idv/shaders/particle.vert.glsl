in vec4 model_vertex; // The location of the vertex in model space
in float in_radius;
flat out vec4 v_model;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;

void main()
{
    v_model = model_vertex;
    inverse_proj = inverse(projection);
    // inverse model-view-matrix
    inverse_mvm = inverse(modelview);
    inverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * model_vertex;
    gl_PointSize = in_radius * scale;

}
