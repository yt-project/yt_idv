bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir) {

    vec3 offset_pos = get_offset_texture_position(ds_tex[0], tex_curr_pos);
    vec3 tex_sample = texture(ds_tex[0], offset_pos).rgb;
    vec3 offset_bmap_pos = get_offset_texture_position(bitmap_tex, tex_curr_pos);
    float map_sample = texture(bitmap_tex, offset_bmap_pos).r;
    if (map_sample > 0.0) {
        // the g channel accumulates the path length over the same steps that
        // contribute to the integral in the r channel. Since the texture values
        // are min/max normalized, the path length is required to recover the
        // integral of the un-normalized values (see
        // BlockRendering.rendered_image_plane). Note that only the r channel
        // is used in the final color output (apply_colormap only uses r)
        float ds = length(tdelta * dir);
        float val = ds * tex_sample.r + curr_color.r;
        curr_color = vec4(val, curr_color.g + ds, val, 1.0);
    }
    return bool(map_sample > 0.0);
}

vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1)
{
  return vec4(curr_color);
}
