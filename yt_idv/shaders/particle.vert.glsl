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
    inverse_proj = inverse(projection);
    // inverse model-view-matrix
    inverse_mvm = inverse(modelview);
    inverse_pmvm = inverse(projection * modelview);
    vradius = in_radius * scale;
    field_value = in_field_value;

    gl_Position = clamp(projection * modelview * (position + vradius * normalize(inverse_pmvm * vec4(model_vertex, clip_pos.zw))),
                        clip_pos - max_particle_size/2.0,
                        clip_pos + max_particle_size/2.0);
    gl_Position.zw = clip_pos.zw;

    UV = model_vertex;
}
