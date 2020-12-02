#version 330 core

layout ( points ) in;
layout ( triangle_strip, max_vertices = 36 ) out;

uniform mat4 modelview;
uniform mat4 projection;

flat in vec3 vdx[];
flat in vec3 vleft_edge[];
flat in vec3 vright_edge[];

flat out vec3 dx;
flat out vec3 left_edge;
flat out vec3 right_edge;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;


flat in mat4 vinverse_proj[];
flat in mat4 vinverse_mvm[];
flat in mat4 vinverse_pmvm[];

uniform vec4 arrangement[36] = vec4[](
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(0.0, 0.0, 1.0, 1.0),
   vec4(0.0, 1.0, 1.0, 1.0),
   vec4(1.0, 1.0, 0.0, 1.0),
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(0.0, 1.0, 0.0, 1.0),
   vec4(1.0, 0.0, 1.0, 1.0),
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(1.0, 0.0, 0.0, 1.0),
   vec4(1.0, 1.0, 0.0, 1.0),
   vec4(1.0, 0.0, 0.0, 1.0),
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(0.0, 1.0, 1.0, 1.0),
   vec4(0.0, 1.0, 0.0, 1.0),
   vec4(1.0, 0.0, 1.0, 1.0),
   vec4(0.0, 0.0, 1.0, 1.0),
   vec4(0.0, 0.0, 0.0, 1.0),
   vec4(0.0, 1.0, 1.0, 1.0),
   vec4(0.0, 0.0, 1.0, 1.0),
   vec4(1.0, 0.0, 1.0, 1.0),
   vec4(1.0, 1.0, 1.0, 1.0),
   vec4(1.0, 0.0, 0.0, 1.0),
   vec4(1.0, 1.0, 0.0, 1.0),
   vec4(1.0, 0.0, 0.0, 1.0),
   vec4(1.0, 1.0, 1.0, 1.0),
   vec4(1.0, 0.0, 1.0, 1.0),
   vec4(1.0, 1.0, 1.0, 1.0),
   vec4(1.0, 1.0, 0.0, 1.0),
   vec4(0.0, 1.0, 0.0, 1.0),
   vec4(1.0, 1.0, 1.0, 1.0),
   vec4(0.0, 1.0, 0.0, 1.0),
   vec4(0.0, 1.0, 1.0, 1.0),
   vec4(1.0, 1.0, 1.0, 1.0),
   vec4(0.0, 1.0, 1.0, 1.0),
   vec4(1.0, 0.0, 1.0, 1.0));

void main() {
    // gl_PositionIn[0] is left edge
    // gl_PositionIn[1] is right edge

    //left_edge = (inverse_pmvm[0] * gl_in[0].gl_Position).xyz;
    //right_edge = (inverse_pmvm[1] * gl_in[1].gl_Position).xyz;

    vec3 width = vright_edge[0] - vleft_edge[0];

    vec4 newPos = vec4(0,0,0,1.0);

    for (int i = 0; i < 12; i++) {
        for (int j = 0; j < 3; j++) {
            newPos = vec4(vleft_edge[0] + width * arrangement[i*3+j].xyz, 1.0);
            gl_Position = projection * modelview * newPos;
            left_edge = vleft_edge[0];
            right_edge = vright_edge[0];
            inverse_pmvm = vinverse_pmvm[0];
            inverse_proj = vinverse_proj[0];
            inverse_mvm = vinverse_mvm[0];
            dx = vdx[0];
            EmitVertex();
        }
        EndPrimitive();
    }

}
