in vec2 model_vertex;
in vec3 position_field; // The location of the vertex in model space
in float radius_field;
in float color_field;

flat out float vradius;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out float field_value;
flat out vec4 v_model;

out vec2 UV;

void main()
{
    v_model = vec4(position_field, 1.0);
    vec4 clip_pos = projection * modelview * v_model;
    inverse_pmvm = inv_pmvm;
    if(radius_field==0.0) {
        vradius = scale;
    } else {
        vradius = radius_field*scale;
    }
    if (color_field == 0.0) {
        field_value = 1.0;
    } else {
        field_value = color_field;
    }

    vec2 leftCorner, rightCorner;

    leftCorner = (projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(-1.0, -1.0, clip_pos.zw)))).xy;
    rightCorner = (projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(1.0, 1.0, clip_pos.zw)))).xy;

    // Making radius zero will make our vertices degenerate and serve as a filter.
    if (max_particle_size > 0.0) {
        vradius *= float(distance(rightCorner, leftCorner) < max_particle_size);
    }

    gl_Position = projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(model_vertex, clip_pos.zw)));
    gl_Position.zw = clip_pos.zw;

    UV = model_vertex;
}
