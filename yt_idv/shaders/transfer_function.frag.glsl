bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir)
{
    float tm = tf_min;
    float tp = tf_max;
    vec4 tf_sample;

    vec3 offset_bmap_pos = get_bitmap_texture_position(tex_curr_pos);
    float map_sample = texture(bitmap_tex, offset_bmap_pos).r;
    if (!(map_sample > 0.0)) return false;

    vec3 offset_pos = get_offset_texture_position(data_tex, tex_curr_pos);
    float tex_sample = texture(data_tex, offset_pos).r;

    if (tf_log > 0.5) {
       if(tex_sample <= 0.0) return false;
       tex_sample = log(tex_sample);
       tm = log(tm);
       tp = log(tp);
    }

    if(tex_sample < tm) return false;
    if(tex_sample > tp) return false;
    vec2 tex_sample_norm = vec2((tex_sample - tm)/(tp - tm), 0.5);
    tf_sample = texture(tf_tex, tex_sample_norm);
    float dt = length(tdelta * dir);
    // front to back: each sample lies behind what the ray has accumulated
    // exact over the step: thin steps add dt * rgb as before; thick or very
    // opaque ones saturate at rgb / a instead of overshooting. This uses an
    // exponent for a few reasons -- one of the big ones is that even though we
    // approach correct values without it, we end up not being able to get the
    // colors correct.  Using the exact value helps get us to being able to
    // saturate with high-opacities.  In general it's the same for low optical
    // depth but in the cases where the step size results in a roughly
    // optically-thick step, we end up in the situation that it simply blows
    // out rather than looking right. Tests suggest that exponents are not
    // *that* expensive, and that the conditional / branching to detect optical
    // thickness might even cost a bit more.  So I guess we should do it.
    float tau = dt * tf_sample.a;
    float absorbed = 1.0 - exp(-tau);
    float emitted = tau > 1e-6 ? absorbed / tf_sample.a : dt;
    curr_color.rgb += (1.0 - curr_color.a) * emitted * tf_sample.rgb;
    curr_color.a += (1.0 - curr_color.a) * absorbed;
    return true;
}

vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1)
{
  // It's possible we need to scale, in which case this may be useful:
  // vec3 p0 = v_camera_pos.xyz + dir * t0;
  // vec3 p1 = v_camera_pos.xyz + dir * t1;
  //return vec4(curr_color.r, curr_color.g, curr_color.b,
  //            curr_color.a * length(p1-p0));
  return curr_color;
}
