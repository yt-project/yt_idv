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

vec3 transform_vec3(vec3 v) {
    if (is_spherical) {
        int theta = 2;
        int phi = 1;
        return vec3(
            v[0] * sin(v[phi]) * cos(v[theta]),
            v[0] * sin(v[phi]) * sin(v[theta]),
            v[0] * cos(v[phi])
        );
    } else {
        return v;
    }
}

vec4 transform_vec4(vec4 v) {
    vec3 v3 = transform_vec3(vec3(v));
    return vec4(v3[0], v3[1], v3[2], v[3]);
}

void main()
{
    vv_model = transform_vec4(model_vertex);
    vinverse_proj = inverse(projection);
    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * transform_vec4(model_vertex);
    vdx = vec3(in_dx);
    vec3 temp_left_edge = transform_vec3(in_left_edge);
    vec3 temp_right_edge = transform_vec3(in_right_edge);
    vleft_edge = min(temp_left_edge, temp_right_edge);
    vright_edge = max(temp_left_edge, temp_right_edge);
}
