

bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir)
{

    vec3 offset_pos = get_offset_texture_position(ds_tex, tex_curr_pos);
    vec3 tex_sample = texture(ds_tex, offset_pos).rgb;
    vec3 offset_bmap_pos = get_offset_texture_position(bitmap_tex, tex_curr_pos);
    float map_sample = texture(bitmap_tex, offset_bmap_pos).r;
    if ((map_sample > 0.0) && (length(curr_color.rgb) < length(tex_sample))) {
        curr_color = vec4(tex_sample, 1.0);
    }
    return bool(map_sample > 0.0);
}

vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1)
{
  return vec4(curr_color);
}
