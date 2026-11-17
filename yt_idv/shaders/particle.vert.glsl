in vec2 model_vertex;
in vec3 position_field; // The location of the vertex in model space
in float radius_field;
in float color_field;
in float particle_volume; // m / rho, zero if not supplied

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
    vec4 view_pos = modelview * v_model;
    vec4 clip_pos = projection * view_pos;
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
    // SPH projection weight, m / (rho h^2), as in yt's pixelize_sph_kernel_projection
    if (particle_volume > 0.0) {
        field_value *= particle_volume / (vradius * vradius);
    }

    // Making radius zero will make our vertices degenerate and serve as a filter.
    if (max_particle_size > 0.0) {
        float screen_radius = vradius * projection[0][0] / clip_pos.w;
        vradius *= float(screen_radius < max_particle_size);
    }

    view_pos.xy += vradius * model_vertex;
    gl_Position = projection * view_pos;

    UV = model_vertex;
}
