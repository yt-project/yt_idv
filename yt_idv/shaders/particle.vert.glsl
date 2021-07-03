in vec4 model_vertex; // The location of the vertex in model space
in float in_radius;
in float in_field_value;

flat out float vradius;
flat out mat4 vinverse_proj;
flat out mat4 vinverse_mvm;
flat out mat4 vinverse_pmvm;
flat out float vfield_value;
flat out vec4 vv_model;

void main()
{
    vv_model = model_vertex;
    vinverse_proj = inverse(projection);
    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * model_vertex;
    vradius = in_radius * scale;
    vfield_value = in_field_value;

}
