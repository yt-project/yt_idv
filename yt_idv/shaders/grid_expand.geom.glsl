layout ( points ) in;
layout ( triangle_strip, max_vertices = 14 ) out;

flat in vec3 vdx[];
flat in vec3 vleft_edge[];
flat in vec3 vright_edge[];

flat out vec3 dx;
flat out vec3 left_edge;
flat out vec3 right_edge;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
out vec4 v_model;

flat in mat4 vinverse_proj[];
flat in mat4 vinverse_mvm[];
flat in mat4 vinverse_pmvm[];
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

void main() {

    vec4 center = gl_in[0].gl_Position;

    vec3 width = vright_edge[0] - vleft_edge[0];

    vec4 newPos;

    for (int i = 0; i < 14; i++) {
        newPos = vec4(transform_vec3(vleft_edge[0] + width * arrangement[aindex[i]]), 1.0);
        gl_Position = projection * modelview * newPos;
        left_edge = vleft_edge[0];
        right_edge = vright_edge[0];
        inverse_pmvm = vinverse_pmvm[0];
        inverse_proj = vinverse_proj[0];
        inverse_mvm = vinverse_mvm[0];
        dx = vdx[0];
        v_model = newPos;
        texture_offset = ivec3(0);
        EmitVertex();
    }

}
