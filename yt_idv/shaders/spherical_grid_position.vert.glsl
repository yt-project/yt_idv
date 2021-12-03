in vec4 model_vertex; // The location of the vertex in model space
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;
flat out vec4 vv_model;
flat out mat4 vinverse_proj;
flat out mat4 vinverse_mvm;
flat out mat4 vinverse_pmvm;
flat out vec3 vdx;
flat out vec3 vleft_edge;
flat out vec3 vright_edge;

vec4 spherical_to_cartesian4(vec4 v) {
    int theta = 2;
    int phi = 1;
    return vec4(
        v[0] * sin(v[phi]) * cos(v[theta]),
        v[0] * sin(v[phi]) * sin(v[theta]),
        v[0] * cos(v[phi]),
        v[3]
    );
}

vec3 spherical_to_cartesian3(vec3 v) {
    int theta = 2;
    int phi = 1;
    return vec3(
        v[0] * sin(v[phi]) * cos(v[theta]),
        v[0] * sin(v[phi]) * sin(v[theta]),
        v[0] * cos(v[phi])
    );
}

void main()
{
    vv_model = spherical_to_cartesian4(model_vertex);
    vinverse_proj = inverse(projection);
    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * vv_model;
    vdx = in_dx;
    vleft_edge = spherical_to_cartesian3(in_left_edge);
    vright_edge = spherical_to_cartesian3(in_right_edge);
}
