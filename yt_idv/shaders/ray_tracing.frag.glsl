in vec4 v_model; // spherical
flat in vec3 dx;  // spherical
flat in vec3 left_edge;  // spherical
flat in vec3 right_edge;  // spherical
flat in mat4 inverse_proj;  // cartesian
flat in mat4 inverse_mvm; // cartesian
flat in mat4 inverse_pmvm; // cartesian
flat in ivec3 texture_offset;
out vec4 output_color;

bool within_bb(vec3 pos)
{
    bvec3 left =  greaterThanEqual(pos, left_edge);
    bvec3 right = lessThanEqual(pos, right_edge);
    return all(left) && all(right);
}

vec3 transform_vec3(vec3 v) {
    if (is_spherical) {
        return vec3(
            v[id_r] * sin(v[id_phi]) * cos(v[id_theta]),
            v[id_r] * sin(v[id_phi]) * sin(v[id_theta]),
            v[id_r] * cos(v[id_phi])
        );
    } else {
        return v;
    }
}

vec3 get_offset_texture_position(sampler3D tex, vec3 tex_curr_pos)
{
    ivec3 texsize = textureSize(tex, 0); // lod (mipmap level) always 0?
    return (tex_curr_pos * texsize + texture_offset) / texsize;
}

bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir);
vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1);

// This main() function will call a function called sample_texture at every
// step along the ray.  It must be of the form
//   void (vec3 tex_curr_pos, inout vec4 curr_color, float tdelta, float t,
//         vec3 direction);

void sph_main()
{
    vec3 ray_position = v_model.xyz; // now spherical

    vec3 p0 = camera_pos.xyz;
    vec4 curr_color = vec4(0.0);

    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = (ray_position - left_edge) / range;

    // need a bounds check too

    // should get texture position in spherical space
    // cartesian_to_spherical(ray position)

    tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
    bool sampled = sample_texture(tex_curr_pos, curr_color, 0.0, 0.0, vec3(0.0));
    if (sampled) {
        output_color = curr_color;
    } else {
        output_color = vec4(0.0);
    }
}

void main()
{
    // Draws the block outline
    // output_color = vec4(1.0);
    // return;

    // Obtain screen coordinates
    // https://www.opengl.org/wiki/Compute_eye_space_from_window_space#From_gl_FragCoord
    if (is_spherical) {
        sph_main();
        return;
    }

    vec3 ray_position = v_model.xyz;

    // Five samples
    vec3 step_size = dx/sample_factor;
    vec3 dir = -normalize(camera_pos.xyz - ray_position);
    dir = max(abs(dir), 0.0001) * sign(dir);
    vec4 curr_color = vec4(0.0);

    // We need to figure out where the ray intersects the box, if it intersects the box.
    // This will help solve the left/right edge issues.

    vec3 idir = 1.0/dir;
    vec3 tl = (left_edge - camera_pos)*idir;
    vec3 tr = (right_edge - camera_pos)*idir;
    vec3 tmin, tmax;
    bvec3 temp_x, temp_y;
    // These 't' prefixes actually mean 'parameter', as we use in grid_traversal.pyx.

    tmax = vec3(lessThan(dir, vec3(0.0)))*tl+vec3(greaterThanEqual(dir, vec3(0.0)))*tr;
    tmin = vec3(greaterThanEqual(dir, vec3(0.0)))*tl+vec3(lessThan(dir, vec3(0.0)))*tr;
    vec2 temp_t = max(tmin.xx, tmin.yz);
    float t0 = max(temp_t.x, temp_t.y);

    // smallest tmax
    temp_t = min(tmax.xx, tmax.yz);
    float t1 = min(temp_t.x, temp_t.y);
    t0 = max(t0, 0.0);
    // if (t1 <= t0) discard;

    // Some more discussion of this here:
    //  http://prideout.net/blog/?p=64

    vec3 p0 = camera_pos.xyz + dir * t0;
    vec3 p1 = camera_pos.xyz + dir * t1;

    vec3 dxidir = abs(idir)  * step_size;

    temp_t = min(dxidir.xx, dxidir.yz);

    float tdelta = min(temp_t.x, temp_t.y);
    float t = t0;

    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = vec3(0.0);

    bool sampled;
    bool ever_sampled = false;

    vec4 v_clip_coord;
    float f_ndc_depth;
    float depth = 1.0;

    ray_position = p0;

    while(t <= t1) {
        tex_curr_pos = (ray_position - left_edge) / range;  // Scale from 0 .. 1
        // But, we actually need it to be 0 + normalized dx/2 to 1 - normalized dx/2
        tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;

        sampled = sample_texture(tex_curr_pos, curr_color, tdelta, t, dir);

        if (sampled) {
            ever_sampled = true;
            v_clip_coord = projection * modelview * vec4(ray_position, 1.0);
            f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
            depth = min(depth, (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5);

        }

        t += tdelta;
        ray_position += tdelta * dir;

    }

    output_color = cleanup_phase(curr_color, dir, t0, t1);

    if (ever_sampled) {
        gl_FragDepth = depth;
    }
}
