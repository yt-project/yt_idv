in vec2 model_vertex;
in vec4 position; // The location of the vertex in model space
in float in_radius;
in float in_field_value;

flat out float vradius;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out float field_value;
flat out vec4 v_model;

out vec2 UV;

void main()
{
    v_model = position;
    vec4 clip_pos = projection * modelview * position;
    inverse_pmvm = inv_pmvm;
    vradius = in_radius * scale;
    field_value = in_field_value;

    vec2 leftCorner, rightCorner;

    leftCorner = (projection * modelview * (position + vradius * normalize(inverse_pmvm * vec4(-1.0, -1.0, clip_pos.zw)))).xy;
    rightCorner = (projection * modelview * (position + vradius * normalize(inverse_pmvm * vec4(1.0, 1.0, clip_pos.zw)))).xy;

    // Making radius zero will make our vertices degenerate and serve as a filter.
    vradius *= float(distance(rightCorner, leftCorner) < max_particle_size);

    gl_Position = projection * modelview * (position + vradius * normalize(inverse_pmvm * vec4(model_vertex, clip_pos.zw)));
    gl_Position.zw = clip_pos.zw;

    UV = model_vertex;
}
