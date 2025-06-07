layout ( points ) in;
layout ( triangle_strip, max_vertices = 4 ) out;

flat out vec4 v_model;
flat out float field_value;

flat in vec4 vv_model[];
flat in float vv_field_value[];


void main() {

    // This is considerably simpler because we will just be doing things based
    // on the positions in clip space
    gl_Position = vec4(
            vv_model[0].x - vv_model[0].z,
            vv_model[0].y - vv_model[0].w,
            0.0,
            0.0
    );
    field_value = vv_field_value[0];
    v_model = vv_model[0];
    EmitVertex();

    gl_Position = vec4(
            vv_model[0].x - vv_model[0].z,
            vv_model[0].y + vv_model[0].w,
            0.0,
            0.0
    );
    field_value = vv_field_value[0];
    v_model = vv_model[0];
    EmitVertex();

    gl_Position = vec4(
            vv_model[0].x + vv_model[0].z,
            vv_model[0].y + vv_model[0].w,
            0.0,
            0.0
    );
    field_value = vv_field_value[0];
    v_model = vv_model[0];
    EmitVertex();

    gl_Position = vec4(
            vv_model[0].x + vv_model[0].z,
            vv_model[0].y - vv_model[0].w,
            0.0,
            0.0
    );
    field_value = vv_field_value[0];
    v_model = vv_model[0];
    EmitVertex();

}
