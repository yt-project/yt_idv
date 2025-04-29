layout ( points ) in;
layout ( triangle_strip, max_vertices = 14 ) out;

flat in vec3 vdx[];
flat in vec3 vleft_edge[];
flat in vec3 vright_edge[];

#ifdef SPHERICAL_GEOM
flat in vec3 vleft_edge_cart[];
flat in vec3 vright_edge_cart[];
flat in vec3 vdx_cart[];
flat out vec3 left_edge_cart;
flat out vec3 right_edge_cart;
flat out vec3 dx_cart;
#endif

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


void main() {

    vec4 center = gl_in[0].gl_Position;
    vec3 width, le;
    vec4 newPos;

    #ifdef NONCARTESIAN_GEOM
    width = vright_edge_cart[0] - vleft_edge_cart[0];
    le = vleft_edge_cart[0];
    #else
    width = vright_edge[0] - vleft_edge[0];
    le = vleft_edge[0];
    #endif

    for (int i = 0; i < 14; i++) {
        // walks through each vertex of the triangle strip, emit it. need to
        // emit gl_Position in cartesian, pass along other attributes in native
        // coordinates

        newPos = vec4(le + width * arrangement[aindex[i]], 1.0);
        gl_Position = projection * modelview * newPos;
        left_edge = vleft_edge[0];
        right_edge = vright_edge[0];
        inverse_pmvm = vinverse_pmvm[0];
        inverse_proj = vinverse_proj[0];
        inverse_mvm = vinverse_mvm[0];

        #ifdef NONCARTESIAN_GEOM
        left_edge_cart = vleft_edge_cart[0];
        right_edge_cart = vright_edge_cart[0];
        dx_cart = vdx_cart[0];
        #endif

        dx = vdx[0];
        v_model = newPos;
        texture_offset = ivec3(0);
        EmitVertex();
    }

}
