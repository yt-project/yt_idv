#version 330 core

layout ( lines ) in;
layout ( triangle_strip, max_vertices = 36 ) out;

void main() {
    // gl_PositionIn[0] is left edge
    // gl_PositionIn[1] is right edge

    vec3 left_edge = gl_in[0].gl_Position.xyz;
    vec3 right_edge = gl_in[1].gl_Position.xyz;

    vec3 width = right_edge - left_edge;

    gl_Position = vec4(0,0,0,1.0);

    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 0.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(0.0, 1.0, 1.0); EmitVertex();
    gl_Position.xyz = left_edge + width * vec3(1.0, 0.0, 1.0); EmitVertex();

}
