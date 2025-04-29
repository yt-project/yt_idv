in vec4 v_model;
flat in vec3 dx;
flat in vec3 left_edge;
flat in vec3 right_edge;
flat in mat4 inverse_proj;
flat in mat4 inverse_mvm;
flat in mat4 inverse_pmvm;
flat in ivec3 texture_offset;

#ifdef NONCARTESIAN_GEOM
flat in vec3 left_edge_cart;
flat in vec3 right_edge_cart;
flat in vec3 dx_cart;
#endif

out vec4 output_color;

bool within_bb(vec3 pos)
{
    bvec3 left =  greaterThanEqual(pos, left_edge);
    bvec3 right = lessThanEqual(pos, right_edge);
    return all(left) && all(right);
}

#ifdef SPHERICAL_GEOM
vec3 cart_to_sphere_vec3(vec3 v) {
    // transform a single point in cartesian coords to spherical
    vec3 vout = vec3(0.,0.,0.);

    // in yt, phi is the azimuth from (0, 2pi), theta is the co-latitude
    // angle (0, pi). the id_ values below are uniforms that depend on the
    // yt dataset coordinate ordering, cart_bbox_* variables are also uniforms
    float x = v[0] * cart_bbox_max_width + cart_bbox_le[0];
    float y = v[1] * cart_bbox_max_width + cart_bbox_le[1];
    float z = v[2] * cart_bbox_max_width + cart_bbox_le[2];
    vout[id_r] = x * x + y * y + z * z;
    vout[id_r] = sqrt(vout[id_r]);
    vout[id_theta] = acos(z / vout[id_r]);
    float phi = atan(y, x);
    // atan2 returns -pi to pi, adjust to (0, 2pi)
    if (phi < 0 ){
        phi = phi + 2.0 * PI;
    }
    vout[id_phi] = phi;

    return vout;

}
#endif

vec3 get_offset_texture_position(sampler3D tex, vec3 tex_curr_pos)
{
    ivec3 texsize = textureSize(tex, 0); // lod (mipmap level) always 0?
    return (tex_curr_pos * texsize + texture_offset) / texsize;
}

bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir);
vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1);

// This main() function will call a function called sample_texture at every
// step along the ray.  sample_texture must be of the form
//   void (vec3 tex_curr_pos, inout vec4 curr_color, float tdelta, float t,
//         vec3 direction);
void main()
{

    // Obtain screen coordinates
    // https://www.opengl.org/wiki/Compute_eye_space_from_window_space#From_gl_FragCoord
    vec3 ray_position = v_model.xyz;
    vec3 ray_position_native;

    output_color = vec4(0.);

    // Five samples
    vec3 dir = -normalize(camera_pos.xyz - ray_position);
    dir = max(abs(dir), 0.0001) * sign(dir);
    vec4 curr_color = vec4(0.0);

    // We need to figure out where the ray intersects the box, if it intersects the box.
    // This will help solve the left/right edge issues.

    vec3 idir = 1.0/dir;
    vec3 tl, tr;
    vec3 dx_effective;
    #ifdef NONCARTESIAN_GEOM
    tl = (left_edge_cart - camera_pos)*idir;
    tr = (right_edge_cart - camera_pos)*idir;
    dx_effective = dx_cart;
    #else
    tl = (left_edge - camera_pos)*idir;
    tr = (right_edge - camera_pos)*idir;
    dx_effective = dx;
    #endif
    vec3 step_size = dx_effective/ sample_factor;

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

    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);  // texture range in native coords
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = vec3(0.0);

    bool sampled;
    bool ever_sampled = false;
    bool within_el = true;

    vec4 v_clip_coord;
    float f_ndc_depth;
    float depth = 1.0;

    ray_position = p0;

    while(t <= t1) {

        // texture position
        #ifdef SPHERICAL_GEOM
        ray_position_native = cart_to_sphere_vec3(ray_position);
        within_el = within_bb(ray_position_native);
        #else
        ray_position_native = ray_position;
        #endif

        if (within_el) {
            tex_curr_pos = (ray_position_native - left_edge) / range;  // Scale from 0 .. 1
            // But, we actually need it to be 0 + normalized dx/2 to 1 - normalized dx/2
            tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
            sampled = sample_texture(tex_curr_pos, curr_color, tdelta, t, dir);
        }

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
