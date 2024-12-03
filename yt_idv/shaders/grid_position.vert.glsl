// note: all in/out variables below are always in native coordinates (e.g.,
// spherical or cartesian) except when noted.

in vec4 model_vertex;
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;

// pre-computed cartesian le, re
in vec3 le_cart;
in vec3 re_cart;

flat out vec4 vv_model;
flat out mat4 vinverse_proj;
flat out mat4 vinverse_mvm;
flat out mat4 vinverse_pmvm;
flat out vec3 vdx;
flat out vec3 vleft_edge;
flat out vec3 vright_edge;

flat out vec3 vleft_edge_cart;
flat out vec3 vright_edge_cart;


void main()
{
    // camera uniforms: projection, modelview
    vv_model = model_vertex;
    vinverse_proj = inverse(projection);

    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * model_vertex;

    // native coordinates
    vdx = vec3(in_dx);
    vleft_edge = vec3(in_left_edge);
    vright_edge = vec3(in_right_edge);

    // cartesian bounding boxes
    vleft_edge_cart = vec3(le_cart);
    vright_edge_cart = vec3(re_cart);
}
