in vec4 v_model;
flat in vec3 dx;
flat in vec3 left_edge;
flat in vec3 right_edge;
flat in mat4 inverse_proj;  // always cartesian
flat in mat4 inverse_mvm; // always cartesian
flat in mat4 inverse_pmvm; // always cartesian
flat in ivec3 texture_offset;
out vec4 output_color;

flat in vec4 phi_plane_le;
flat in vec4 phi_plane_re;

const float INFINITY = 1. / 0.;
const float PI = 3.1415926535897932384626433832795;
bool within_bb(vec3 pos)
{
    bvec3 left =  greaterThanEqual(pos, left_edge);
    bvec3 right = lessThanEqual(pos, right_edge);
    return all(left) && all(right);
}

vec3 transform_vec3(vec3 v) {
    if (is_spherical) {
        return vec3(
            // in yt, phi is the polar angle from (0, 2pi), theta is the azimuthal
            // angle (0, pi). the id_ values below are uniforms that depend on the
            // yt dataset coordinate ordering
            v[id_r] * sin(v[id_theta]) * cos(v[id_phi]),
            v[id_r] * sin(v[id_theta]) * sin(v[id_phi]),
            v[id_r] * cos(v[id_theta])
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

float get_ray_plane_intersection(vec3 p_normal, float p_constant, vec3 ray_origin, vec3 ray_dir)
{
    float n_dot_u = dot(p_normal, ray_dir);
    float n_dot_ro = dot(p_normal, ray_origin);
    // add check for n_dot_u == 0 (ray is parallel to plane)
    if (n_dot_u == float(0.0))
    {
        // the ray is parallel to the plane. there are either no intersections
        // or infinite intersections. In the second case, we are guaranteed
        // to intersect one of the other faces, so we can drop this plane.
        return INFINITY;
    }

    return (p_constant - n_dot_ro) / n_dot_u;
}

vec2 get_ray_sphere_intersection(float r, vec3 ray_origin, vec3 ray_dir)
{
    float dir_dot_dir = dot(ray_dir, ray_dir);
    float ro_dot_ro = dot(ray_origin, ray_origin);
    float dir_dot_ro = dot(ray_dir, ray_origin);
    float rsq = r * r; // could be calculated in vertex shader

    float a_2 = 2.0 * dir_dot_dir;
    float b = 2.0 * dir_dot_ro;
    float c =  ro_dot_ro - rsq;
    float determinate = b*b - 2.0 * a_2 * c;
    float cutoff_val = 0.0;
    if (determinate < cutoff_val)
    {
        return vec2(INFINITY, INFINITY);
    }
    else if (determinate == cutoff_val)
    {
        return vec2(-b / a_2, INFINITY);
    }
    else
    {
        return vec2((-b - sqrt(determinate))/ a_2, (-b + sqrt(determinate))/ a_2);
    }

}

vec2 get_ray_cone_intersection(float theta, vec3 ray_origin, vec3 ray_dir)
{
    // note: cos(theta) and vhat could be calculated in vertex shader
    float costheta;
    vec3 vhat;
    if (theta > PI/2.0)
    {
        // if theta is past PI/2, the cone will point in negative z and the
        // half angle should be measured from the -z axis, not +z.
        vhat = vec3(0.0, 0.0, -1.0);
        costheta = cos(PI - theta);
    }
    else
    {
        vhat = vec3(0.0, 0.0, 1.0);
        costheta = cos(theta);
    }
    float cos2t = pow(costheta, 2);
    // note: theta = PI/2.0 is well defined. determinate = 0 in that case and
    // the cone becomes a plane in x-y.

    float dir_dot_vhat = dot(ray_dir, vhat);
    float dir_dot_dir = dot(ray_dir, ray_dir);
    float ro_dot_vhat = dot(ray_origin, vhat);
    float ro_dot_dir = dot(ray_origin, ray_dir);
    float ro_dot_ro = dot(ray_origin, ray_dir);

    float a_2 = 2.0*(pow(dir_dot_vhat, 2) - dir_dot_dir * cos2t);
    float b = 2.0 * (ro_dot_vhat * dir_dot_vhat - ro_dot_dir*cos2t);
    float c = pow(ro_dot_vhat, 2) - ro_dot_ro*cos2t;
    float determinate = b*b - 2.0 * a_2 * c;
    if (determinate < 0.0)
    {
        return vec2(INFINITY, INFINITY);
    }
    else if (determinate == 0.0)
    {
        return vec2(-b / a_2, INFINITY);
    }
    else
    {
        vec2 t = vec2((-b - sqrt(determinate))/ a_2, (-b + sqrt(determinate))/ a_2);

        // check that t values are not for the shadow cone
        float cutoff_t = (-1.0 * ro_dot_vhat) / dir_dot_vhat;
        if (t[0] < cutoff_t)
        {
            t[0] = INFINITY;
        }
        else if (t[1] < cutoff_t)
        {
            t[1] = INFINITY;
        }
        return t;
    }
}

void spherical_coord_shortcircuit()
{
    vec3 ray_position = v_model.xyz; // now spherical
    vec3 ray_position_xyz = transform_vec3(ray_position); // cartesian
    vec3 p0 = camera_pos.xyz; // cartesian
    vec3 dir = -normalize(camera_pos.xyz - ray_position_xyz);
    vec4 curr_color = vec4(0.0);

    // intersections
    vec2 t_sphere_outer = get_ray_sphere_intersection(right_edge[id_r], ray_position_xyz, dir);
    if (t_sphere_outer[0] == INFINITY && t_sphere_outer[1] == INFINITY)
    {
        // if there are no intersections with the outer sphere, then there
        // will be no intersections with the remaining faces and we can stop
        // looking.
        discard;
    }

    vec2 t_sphere_inner = get_ray_sphere_intersection(left_edge[id_r], ray_position_xyz, dir);
    float t_p_1 = get_ray_plane_intersection(vec3(phi_plane_le), phi_plane_le[3], ray_position_xyz, dir);
    float t_p_2 = get_ray_plane_intersection(vec3(phi_plane_re), phi_plane_re[3], ray_position_xyz, dir);
    vec2 t_cone_outer = get_ray_cone_intersection(right_edge[id_theta], ray_position_xyz, dir);
    vec2 t_cone_inner= get_ray_cone_intersection(left_edge[id_theta], ray_position_xyz, dir);

    // do the texture evaluation in the native coordinate space
    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = (ray_position - left_edge) / range;

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
        spherical_coord_shortcircuit();
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
