// note: all in/out variables below are always in native coordinates (e.g.,
// spherical or cartesian) except when noted.

in vec4 model_vertex;
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;

in vec4 phi_plane_le;  // first 3 elements are the normal vector, final is constant
in vec4 phi_plane_re;

// pre-computed cartesian le, re
in vec3 le_cart;
in vec3 re_cart;

flat out vec4 vv_model;
flat out mat4 vinverse_proj;  // always cartesian
flat out mat4 vinverse_mvm;  // always cartesian
flat out mat4 vinverse_pmvm; // always cartesian
flat out vec3 vdx;
flat out vec3 vleft_edge;
flat out vec3 vright_edge;

flat out vec4 vphi_plane_le;
flat out vec4 vphi_plane_re;
flat out vec3 vleft_edge_cart;
flat out vec3 vright_edge_cart;

//vec3 transform_vec3(vec3 v) {
//    if (is_spherical) {
//        // in yt, phi is the polar angle from (0, 2pi), theta is the azimuthal
//        // angle (0, pi). the id_ values below are uniforms that depend on the
//        // yt dataset coordinate ordering
//        return vec3(
//            v[id_r] * sin(v[id_theta]) * cos(v[id_phi]),
//            v[id_r] * sin(v[id_theta]) * sin(v[id_phi]),
//            v[id_r] * cos(v[id_theta])
//        );
//    } else {
//        return v;
//    }
//}
//
//vec4 transform_vec4(vec4 v) {
////    vec3 v3 = transform_vec3(vec3(v));
//    return vec4(v3[0], v3[1], v3[2], v[3]);
//}

void main()
{
    // camera uniforms:
    // projection, modelview
    vv_model = model_vertex;
    vinverse_proj = inverse(projection);

    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inverse(projection * modelview);
    gl_Position = projection * modelview * vv_model; //transform_vec4(model_vertex);

    // spherical
    vdx = vec3(in_dx);
    vleft_edge = vec3(in_left_edge);
    vright_edge = vec3(in_right_edge);

    // pre-computed phi-plane info
    vphi_plane_le = vec4(phi_plane_le);
    vphi_plane_re = vec4(phi_plane_re);

    // cartesian bounding boxes
    vleft_edge_cart = vec3(le_cart);
    vright_edge_cart = vec3(re_cart);
}
