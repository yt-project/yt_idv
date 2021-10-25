in vec4 v_model;
flat in vec3 dx;
flat in vec3 left_edge;
flat in vec3 right_edge;
flat in mat4 inverse_proj;
flat in mat4 inverse_mvm;
flat in mat4 inverse_pmvm;
flat in ivec3 texture_offset;
out vec4 output_color;

bool within_bb(vec3 pos)
{
    bvec3 left =  greaterThanEqual(pos, left_edge);
    bvec3 right = lessThanEqual(pos, right_edge);
    return all(left) && all(right);
}

vec3 get_offset_texture_position(sampler3D tex, vec3 tex_curr_pos)
{
    ivec3 texsize = textureSize(tex, 0); // lod (mipmap level) always 0?
    return (tex_curr_pos * texsize + texture_offset) / texsize;
}

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

// This main() function will call a function called sample_texture at every
// step along the ray.  It must be of the form
//   void (vec3 tex_curr_pos, inout vec4 curr_color, float tdelta, float t,
//         vec3 direction);

void main()
{
    // Obtain screen coordinates
    // https://www.opengl.org/wiki/Compute_eye_space_from_window_space#From_gl_FragCoord
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
    if (t1 <= t0) discard;

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

    bool is_layer = false;
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
            for (int i = 0; i < iso_num_layers; i++) {
                if (abs(length(curr_color.rgb) - iso_layers[i]) <= iso_tolerance) {
                    is_layer = true;
                    break;
                }
            }
            if (is_layer) {
                break;
            }
        }

        t += tdelta;
        ray_position += tdelta * dir;

    }

    output_color = cleanup_phase(curr_color, dir, t0, t1);

    if (ever_sampled) {
        gl_FragDepth = depth;
    } 
    if (!is_layer) {
        output_color = vec4(0.0, 0.0, 0.0, 0.0);
    }
}
