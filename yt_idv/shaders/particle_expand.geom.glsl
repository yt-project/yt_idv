layout ( points ) in;
layout ( triangle_strip, max_vertices = 4 ) out;

flat in float vradius[];
flat in float vfield_value[];

flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out vec4 v_model;
flat out float field_value;
flat out float radius;

out vec2 UV;

flat in mat4 vinverse_proj[];
flat in mat4 vinverse_mvm[];
flat in mat4 vinverse_pmvm[];
flat in vec4 vv_model[];
flat in vec3 vv_camera_pos[];

// https://stackoverflow.com/questions/28375338/cube-using-single-gl-triangle-strip
// suggests that the triangle strip we want for the cube is

uniform vec3 arrangement[8] = vec3[](
    vec3(-1, -1, -1),
    vec3(1, -1, -1),
    vec3(-1, 1, -1),
    vec3(1, 1, -1),
    vec3(-1, -1, 1),
    vec3(1, -1, 1),
    vec3(-1, 1, 1),
    vec3(1, 1, 1)
);

void main() {

    vec4 cornerPos;
    vec2 cornerFrag;
    vec4 position = vv_model[0];

    mat4 pmvm = projection * modelview;

    vec2 fragLeftCorner, fragRightCorner;
    fragLeftCorner = fragRightCorner = gl_in[0].gl_Position.xy;

    // This is definitely not the smartest way to do this!  We should be
    // computing something in the clip/normal space.  We can take advantage of
    // the fact that our sphere will always have at least one radial vector that
    // is perpendicular to the eye vector.

    for (int i = 0; i < 8; i++) { 
        cornerPos = position + vec4(arrangement[i], 0.0) * vradius[0];
        cornerFrag = (projection * modelview * cornerPos).xy;
        fragLeftCorner.x = min(fragLeftCorner.x, cornerFrag.x);
        fragLeftCorner.y = min(fragLeftCorner.y, cornerFrag.y);
        fragRightCorner.x = max(fragRightCorner.x, cornerFrag.x);
        fragRightCorner.y = max(fragRightCorner.y, cornerFrag.y);
    }

    // We don't want to allow each particle to be bigger than some maximum size
    // in clip space coordinates.
    fragLeftCorner.x = max(fragLeftCorner.x, gl_in[0].gl_Position.x - max_particle_size/2.0);
    fragRightCorner.x = min(fragRightCorner.x, gl_in[0].gl_Position.x + max_particle_size/2.0);

    fragLeftCorner.y = max(fragLeftCorner.y, gl_in[0].gl_Position.y - max_particle_size/2.0);
    fragRightCorner.y = min(fragRightCorner.y, gl_in[0].gl_Position.y + max_particle_size/2.0);

    // https://stackoverflow.com/questions/12239876/fastest-way-of-converting-a-quad-to-a-triangle-strip
    // or: https://en.wikipedia.org/wiki/Triangle_strip
    // in section "OpenGL implementation" this corresponds to A = 1, B = 2, C = 3, D = 4 

    gl_Position = vec4(fragLeftCorner.xy, gl_in[0].gl_Position.zw);
    field_value = vfield_value[0];
    v_model = vv_model[0];
    radius = vradius[0];
    UV = vec2(-1.0, -1.0);
    EmitVertex();

    gl_Position = vec4(fragLeftCorner.x, fragRightCorner.y, gl_in[0].gl_Position.zw);
    field_value = vfield_value[0];
    v_model = vv_model[0];
    radius = vradius[0];
    UV = vec2(-1.0, +1.0);
    EmitVertex();

    gl_Position = vec4(fragRightCorner.x, fragLeftCorner.y, gl_in[0].gl_Position.zw);
    field_value = vfield_value[0];
    v_model = vv_model[0];
    radius = vradius[0];
    UV = vec2(+1.0, -1.0);
    EmitVertex();

    gl_Position = vec4(fragRightCorner.xy, gl_in[0].gl_Position.zw);
    field_value = vfield_value[0];
    v_model = vv_model[0];
    radius = vradius[0];
    UV = vec2(+1.0, +1.0);
    EmitVertex();

}
