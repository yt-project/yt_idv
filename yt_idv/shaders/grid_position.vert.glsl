in vec4 model_vertex; // The location of the vertex in model space
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;
flat out vec4 vv_model;  // spherical
flat out mat4 vinverse_proj;  // cartesian
flat out mat4 vinverse_mvm; // cartesian
flat out mat4 vinverse_pmvm; // cartesian
flat out vec3 vdx; // spherical
flat out vec3 vleft_edge; // spherical
flat out vec3 vright_edge; // spherical

vec3 transform_vec3(vec3 v) {
    if (is_spherical) {
        return vec3(
            v[id_r] * sin(v[id_phi]) * cos(v[id_theta]),
            v[id_r] * sin(v[id_phi]) * sin(v[id_theta]),
            v[id_r] * cos(v[id_phi])
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
    // camera uniforms:
    // projection, modelview
    vv_model = model_vertex; //spherical coords
    vinverse_proj = inverse(projection);
    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * transform_vec4(model_vertex);
    vdx = vec3(in_dx);  // spherical coords
    vleft_edge = vec3(in_left_edge); // spherical coords
    vright_edge = vec3(in_right_edge); // spheerical coords
}
