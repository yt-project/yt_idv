layout ( points ) in;
layout ( triangle_strip, max_vertices = 14 ) out;

// note: all in/out variables below are always in native coordinates (e.g.,
// spherical or cartesian) except when noted.
flat in vec3 vdx[];
flat in vec3 vleft_edge[];
flat in vec3 vright_edge[];

flat out vec3 dx;
flat out vec3 left_edge;
flat out vec3 right_edge;
flat out mat4 inverse_proj; // always cartesian
flat out mat4 inverse_mvm; // always cartesian
flat out mat4 inverse_pmvm; // always cartesian
out vec4 v_model;

flat in mat4 vinverse_proj[];  // always cartesian
flat in mat4 vinverse_mvm[]; // always cartesian
flat in mat4 vinverse_pmvm[]; // always cartesian
flat in vec4 vv_model[];

flat out ivec3 texture_offset;

// https://stackoverflow.com/questions/28375338/cube-using-single-gl-triangle-strip
// suggests that the triangle strip we want for the cube is

uniform vec3 arrangement[8] = vec3[](
    vec3(0, 0, 0),
    vec3(1, 0, 0),
    vec3(0, 1, 0),
    vec3(1, 1, 0),
    vec3(0, 0, 1),
    vec3(1, 0, 1),
    vec3(0, 1, 1),
    vec3(1, 1, 1)
);

uniform int aindex[14] = int[](6, 7, 4, 5, 1, 7, 3, 6, 2, 4, 0, 1, 2, 3);

vec3 transform_vec3(vec3 v) {
    if (is_spherical) {
        // in yt, phi is the polar angle from (0, 2pi), theta is the azimuthal
        // angle (0, pi). the id_ values below are uniforms that depend on the
        // yt dataset coordinate ordering
        return vec3(
            v[id_r] * sin(v[id_theta]) * cos(v[id_phi]),
            v[id_r] * sin(v[id_theta]) * sin(v[id_phi]),
            v[id_r] * cos(v[id_theta])
        );
    } else {
        return v;
    }
}

void main() {

    vec4 center = gl_in[0].gl_Position;  // always cartesian

    vec3 width = vright_edge[0] - vleft_edge[0];

    vec4 newPos;
    vec3 current_pos;

    for (int i = 0; i < 14; i++) {
        // walks through each vertex of the triangle strip, emit it. need to
        // emit gl_Position in cartesian, but pass native coords out in v_model
        current_pos = vec3(vleft_edge[0] + width * arrangement[aindex[i]]);
        newPos = vec4(transform_vec3(current_pos), 1.0); // cartesian
        gl_Position = projection * modelview * newPos;  // cartesian
        left_edge = vleft_edge[0];
        right_edge = vright_edge[0];
        inverse_pmvm = vinverse_pmvm[0];
        inverse_proj = vinverse_proj[0];
        inverse_mvm = vinverse_mvm[0];
        dx = vdx[0];
        v_model = vec4(current_pos, 1.0);
        texture_offset = ivec3(0);
        EmitVertex();
    }
}
