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

#ifdef SPHERICAL_GEOM
vec3 cart_to_sphere_vec3(vec3 v) {
    // transform a single point in cartesian coords to spherical
    vec3 vout = vec3(0.,0.,0.);

    // in yt, phi is the azimuth from (0, 2pi), theta is the co-latitude
    // angle (0, pi). the id_ values below are uniforms that depend on the
    // yt dataset coordinate ordering, cart_bbox_* variables are also uniforms
    vout[id_r] = v[0] * v[0] + v[1] * v[1] + v[2] * v[2];
    vout[id_r] = sqrt(vout[id_r]);
    vout[id_theta] = acos(v[2] / vout[id_r]);
    float phi = atan(v[1], v[0]);
    // atan2 returns -pi to pi, adjust to (0, 2pi)
    if (phi < 0 ){
        phi = phi + 2.0 * PI;
    }
    vout[id_phi] = phi;

    return vout;
}

// max number of ray-surface crossings tracked for a single element: 4 from
// the two spherical surfaces, 4 from the two conical surfaces, 2 from the two
// phi-planes and the 2 bounding values of the ray parameter.
const int MAX_ISECTS = 12;
// max number of distinct entry-exit pairs within a single element
const int MAX_SEGMENTS = 4;
// upper bound on the samples taken within a single entry-exit pair
const int MAX_SEGMENT_SAMPLES = 1024;
const float ISECT_TINY = 1.0e-8;
const float ISECT_TINY_ANGLE = 1.0e-5;

int solve_quadratic(float a, float hb, float c, float hdisc, out vec2 roots)
{
    // roots of a*t^2 + 2*hb*t + c, given the half-discriminant hb^2 - a*c.
    // the callers supply hdisc directly because forming it from a, hb and c
    // loses too much precision for the near-degenerate conical surfaces.
    roots = vec2(0.0);
    if (abs(a) < ISECT_TINY) {
        if (abs(hb) < ISECT_TINY) return 0;
        roots[0] = -0.5 * c / hb;
        return 1;
    }
    if (hdisc < 0.0) return 0;
    float sq = sqrt(hdisc);
    float q = -(hb + (hb >= 0.0 ? sq : -sq));
    roots[0] = q / a;
    roots[1] = abs(q) > ISECT_TINY ? c / q : roots[0];
    return 2;
}

int add_isect(float t, float tmin, float tmax, inout float ts[MAX_ISECTS], int n)
{
    if (n >= MAX_ISECTS) return n;
    if (t <= tmin || t >= tmax) return n;
    ts[n] = t;
    return n + 1;
}

int ray_surface_isects(vec3 ro, vec3 rd, float tmin, float tmax,
                       inout float ts[MAX_ISECTS])
{
    // ray parameters at which the ray crosses one of the surfaces bounding the
    // spherical volume element, restricted to (tmin, tmax) and returned in
    // ascending order with tmin, tmax included.
    vec2 roots;
    int nroots;

    ts[0] = tmin;
    ts[1] = tmax;
    int n = 2;

    float dd = dot(rd, rd);
    float od = dot(ro, rd);
    float oo = dot(ro, ro);

    // spherical surfaces at constant r
    for (int i = 0; i < 2; i++) {
        float rad = i == 0 ? left_edge[id_r] : right_edge[id_r];
        if (rad < ISECT_TINY) continue;
        float c = oo - rad * rad;
        nroots = solve_quadratic(dd, od, c, od * od - dd * c, roots);
        for (int j = 0; j < nroots; j++) {
            n = add_isect(roots[j], tmin, tmax, ts, n);
        }
    }

    // conical surfaces at constant theta: z^2 = cos(theta)^2 * (x^2+y^2+z^2).
    // for theta of pi/2 the cone is the z=0 plane and the quadratic has a
    // double root there, which the factored half-discriminant recovers exactly.
    for (int i = 0; i < 2; i++) {
        float th = i == 0 ? left_edge[id_theta] : right_edge[id_theta];
        if (abs(sin(th)) < ISECT_TINY_ANGLE) continue;  // cone collapses to the z axis
        float k2 = cos(th) * cos(th);
        float hdisc = k2 * (rd.z * rd.z * oo + dd * ro.z * ro.z
                            - 2.0 * ro.z * rd.z * od + k2 * (od * od - dd * oo));
        nroots = solve_quadratic(rd.z * rd.z - k2 * dd,
                                 ro.z * rd.z - k2 * od,
                                 ro.z * ro.z - k2 * oo,
                                 hdisc,
                                 roots);
        for (int j = 0; j < nroots; j++) {
            n = add_isect(roots[j], tmin, tmax, ts, n);
        }
    }

    // planes at constant phi, containing the z axis
    for (int i = 0; i < 2; i++) {
        float ph = i == 0 ? left_edge[id_phi] : right_edge[id_phi];
        vec3 nrm = vec3(-sin(ph), cos(ph), 0.0);
        float den = dot(nrm, rd);
        if (abs(den) < ISECT_TINY) continue;
        n = add_isect(-dot(nrm, ro) / den, tmin, tmax, ts, n);
    }

    for (int i = 1; i < n; i++) {
        float key = ts[i];
        int j = i - 1;
        while (j >= 0 && ts[j] > key) {
            ts[j + 1] = ts[j];
            j--;
        }
        ts[j + 1] = key;
    }

    return n;
}

int ray_element_segments(vec3 ro, vec3 rd, float tmin, float tmax,
                         inout float seg_entry[MAX_SEGMENTS],
                         inout float seg_exit[MAX_SEGMENTS])
{
    // entry-exit pairs of the ray within the spherical volume element. the
    // surface crossings bound sub-intervals that are either entirely inside or
    // entirely outside the element, so a single interior point of each
    // sub-interval decides it.
    float ts[MAX_ISECTS];
    int nt = ray_surface_isects(ro, rd, tmin, tmax, ts);

    int nseg = 0;
    for (int i = 0; i < nt - 1; i++) {
        float ta = ts[i];
        float tb = ts[i + 1];
        if (tb - ta < ISECT_TINY) continue;
        vec3 pmid = ro + rd * (0.5 * (ta + tb));
        if (!within_bb(cart_to_sphere_vec3(pmid), left_edge, right_edge)) continue;
        if (nseg > 0 && ta - seg_exit[nseg - 1] < ISECT_TINY) {
            seg_exit[nseg - 1] = tb;
        } else if (nseg < MAX_SEGMENTS) {
            seg_entry[nseg] = ta;
            seg_exit[nseg] = tb;
            nseg++;
        }
    }

    return nseg;
}

float spherical_step_size(vec3 ro, vec3 rd, float t_entry, float t_exit)
{
    // the sampling length along the ray, set by the smallest of the
    // characteristic lengths of the volume element,
    //     dr,  r * dtheta,  r * sin(theta) * dphi
    // scaled by the sampling factor eta. in spherical coordinates the
    // sample_factor uniform holds log10(eta).
    //
    // r and theta are evaluated at the ray's closest approach to the origin,
    // restricted to the portion of the ray within the element.
    float t_eval = clamp(-dot(ro, rd) / dot(rd, rd), t_entry, t_exit);
    vec3 p_eval = cart_to_sphere_vec3(ro + rd * t_eval);

    // guard r using 1% of the radial cell width, so that r never drops below a
    // physical fraction of the voxel regardless of units, and guard theta using
    // 1% of the angular cell width, for consistent pole behavior across grids.
    float r_guarded = max(p_eval[id_r], left_edge[id_r] + 0.01 * dx[id_r]);
    float sin_theta_guarded = max(sin(p_eval[id_theta]), sin(0.01 * dx[id_theta]));

    float ds = min(dx[id_r], min(r_guarded * dx[id_theta],
                                 r_guarded * sin_theta_guarded * dx[id_phi]));

    return pow(10.0, sample_factor) * ds;
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

    #ifdef SPHERICAL_GEOM
    // the step size varies with position within the element, it is set for
    // each ray entry/exit pair below.
    float tdelta = 0.0;
    #else
    vec3 step_size = dx_effective / sample_factor;
    vec3 dxidir = abs(idir)  * step_size;

    temp_t = min(dxidir.xx, dxidir.yz);

    float tdelta = min(temp_t.x, temp_t.y);
    #endif
    float t = t0;

    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);  // texture range in native coords
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = vec3(0.0);

    bool sampled = false;
    bool ever_sampled = false;

    vec4 v_clip_coord;
    float f_ndc_depth;
    float depth = 1.0;

    ray_position = p0;

    #ifdef SPHERICAL_GEOM

    // the cartesian bounding box only gives a first cut: walk the true
    // entry-exit pairs of the ray within the spherical volume element.
    float seg_entry[MAX_SEGMENTS];
    float seg_exit[MAX_SEGMENTS];
    int nseg = ray_element_segments(camera_pos.xyz, dir, t0, t1,
                                    seg_entry, seg_exit);
    if (nseg == 0) discard;

    for (int iseg = 0; iseg < nseg; iseg++) {
        float seg_dt = seg_exit[iseg] - seg_entry[iseg];
        // dir is normalized up to the small offset applied above, so the ray
        // parameter maps to path length with length(dir).
        float dt = spherical_step_size(camera_pos.xyz, dir,
                                       seg_entry[iseg], seg_exit[iseg]) / length(dir);
        int nsamples = int(clamp(ceil(seg_dt / dt), 1.0, float(MAX_SEGMENT_SAMPLES)));
        tdelta = seg_dt / float(nsamples);
        for (int isample = 0; isample < nsamples; isample++) {
            t = seg_entry[iseg] + (float(isample) + 0.5) * tdelta;
            ray_position = camera_pos.xyz + t * dir;
            ray_position_native = cart_to_sphere_vec3(ray_position);

            tex_curr_pos = (ray_position_native - left_edge) / range;  // Scale from 0 .. 1
            // But, we actually need it to be 0 + normalized dx/2 to 1 - normalized dx/2
            tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
            sampled = sample_texture(tex_curr_pos, curr_color, tdelta, t, dir);

            if (sampled) {
                ever_sampled = true;
                v_clip_coord = projection * modelview * vec4(ray_position, 1.0);
                f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
                depth = min(depth, (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5);
            }
        }
    }

    t0 = seg_entry[0];
    t1 = seg_exit[nseg - 1];

    #else

    while(t <= t1) {

        ray_position_native = ray_position;

        tex_curr_pos = (ray_position_native - left_edge) / range;  // Scale from 0 .. 1
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

    #endif

    output_color = cleanup_phase(curr_color, dir, t0, t1);

    if (ever_sampled) {
        gl_FragDepth = depth;
    }
}
