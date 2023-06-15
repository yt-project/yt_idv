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

bool within_bb(vec3 pos)
{
    bvec3 left =  greaterThanEqual(pos, left_edge-0.001);
    bvec3 right = lessThanEqual(pos, right_edge+0.001);
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

vec3 reverse_transform_vec3(vec3 v) {
    if (is_spherical) {
        vec3 vout = vec3(0.);
        vout[id_r] = length(v);
        vout[id_phi] = atan(v[1], v[0]);
        vout[id_theta] = atan(sqrt(v[1]*v[1] + v[0]*v[0]), v[2]);
        return vout;
    } else {
        return v;
    }
}

vec3 ray_position_to_native_coords(float t, vec3 ray_origin, vec3 ray_dir) {
    vec3 xyz = ray_origin + t * ray_dir;
    if (is_spherical){
        return reverse_transform_vec3(xyz);
    }
    return xyz;
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

void get_ray_plane_intersection(inout vec2 t_points, inout int n_points, vec3 p_normal, float p_constant, vec3 ray_origin, vec3 ray_dir)
{
    float n_dot_u = dot(p_normal, ray_dir);
    float n_dot_ro = dot(p_normal, ray_origin);
    // add check for n_dot_u == 0 (ray is parallel to plane)
    if (n_dot_u != float(0.0))
    {
        float t_point = (p_constant - n_dot_ro) / n_dot_u;
        if (within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }
    }
    // otherwise, the ray is parallel to the plane. there are either no intersections
    // or infinite intersections. In the second case, we are guaranteed
    // to intersect the other faces, so we can drop this plane.

}

void get_ray_sphere_intersection(inout vec2 t_points, inout int n_points, float r, vec3 ray_origin, vec3 ray_dir)
{
    // gets called first
    float dir_dot_dir = dot(ray_dir, ray_dir);
    float ro_dot_ro = dot(ray_origin, ray_origin);
    float dir_dot_ro = dot(ray_dir, ray_origin);
    float rsq = r * r; // could be calculated in vertex shader

    float a_2 = 2.0 * dir_dot_dir;
    float b = 2.0 * dir_dot_ro;
    float c =  ro_dot_ro - rsq;
    float determinate = b*b - 2.0 * a_2 * c;
    float t_point;
    if (determinate == 0.0)
    {
        t_point = -b / a_2;
        if (within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }
    }
    else if (determinate > 0.0)
    {

        t_point = (-b - sqrt(determinate))/ a_2;
        if (within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }

        t_point = (-b + sqrt(determinate))/ a_2;
        if (n_points < 2 && within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }
    }

}

void get_ray_cone_intersection(inout vec2 t_points, inout int n_points, float theta, vec3 ray_origin, vec3 ray_dir)
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
    float t_point;
    if (determinate < 0.0)
    {
        return;
    }
    else if (determinate == 0.0)
    {
        t_point = -b / a_2;
        if (within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }
    }
    else
    {
        // note: it is possible to have real solutions that intersect the shadow cone
        // and not the actual cone. those values should be discarded. But they will
        // fail subsequent bounds checks for interesecting the volume, so we can
        // just handle it there instead of adding another check here.
        t_point = (-b - sqrt(determinate))/ a_2;
        if (within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }

        t_point = (-b + sqrt(determinate))/ a_2;
        if (n_points < 2 && within_bb(ray_position_to_native_coords(t_point, ray_origin, ray_dir)))
        {
            t_points[n_points] = t_point;
            n_points = n_points + 1;
        }
    }
}

void spherical_coord_shortcircuit()
{
    vec3 ray_position = v_model.xyz; // now spherical
    vec3 ray_position_xyz = transform_vec3(ray_position); // cartesian
    vec3 p0 = camera_pos.xyz; // cartesian
//    vec3 p0 = ray_position_xyz;
    vec3 dir = -normalize(camera_pos.xyz - ray_position_xyz);
    vec4 curr_color = vec4(0.0);

    // intersections
    vec2 t_points;
    int n_points = 0; // number of intersections found

    // outer sphere
    get_ray_sphere_intersection(t_points, n_points, right_edge[id_r], p0, dir);
    // note: the order of geometry intersections is important. we are not
    // explicitly handling the case of a 3 or 4-point intersection where a ray
    // intersects the two phi-planes and the inner sphere. But by checking the
    // phi-planes first, we will at least sample some of those points.
    // left edge fixed phi-plane
    if (n_points < 2){
        get_ray_plane_intersection(t_points, n_points, vec3(phi_plane_le), phi_plane_le[3], p0, dir);
    }
    // right edge fixed phi-plane
    if (n_points < 2){
        get_ray_plane_intersection(t_points, n_points, vec3(phi_plane_re), phi_plane_re[3], p0, dir);
    }
    // inner sphere
    if (n_points < 2){
        get_ray_sphere_intersection(t_points, n_points, left_edge[id_r], p0, dir);
    }
    // outer cone surface
    if (n_points < 2){
        get_ray_cone_intersection(t_points, n_points, right_edge[id_theta], p0, dir);
    }
    // inner cone surface
    if (n_points < 2){
        get_ray_cone_intersection(t_points, n_points, left_edge[id_theta], p0, dir);
    }

    if (n_points < 1) {
        discard;
    }
    // do the texture evaluation in the native coordinate space
    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec4 v_clip_coord;
    float f_ndc_depth;
    float depth = 1.0;

    // take those t values, get the spherical position for sampling
    if (n_points == 1){

        // single intersection: on cusp. just return a single sample.
        ray_position = ray_position_to_native_coords(t_points[0], p0, dir);
        vec3 tex_curr_pos = (ray_position - left_edge) / range;

        tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
        bool sampled = sample_texture(tex_curr_pos, curr_color, 0.0, 0.0, vec3(0.0));
        if (sampled) {
            output_color = curr_color;
            v_clip_coord = projection * modelview * vec4(transform_vec3(ray_position), 1.0);
            f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
            gl_FragDepth = min(depth, (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5);
        } else {
            output_color = vec4(0.0);
        }
        return;
    }

    // sample once at the midpoint (works?)
    float t_mid = (t_points[1] + t_points[0])/2.;
    ray_position = ray_position_to_native_coords(t_mid, p0, dir);
    vec3 tex_curr_pos = (ray_position - left_edge) / range;

    tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
    bool sampled = sample_texture(tex_curr_pos, curr_color, 0.0, 0.0, vec3(0.0));
    if (sampled) {
        output_color = curr_color;
        v_clip_coord = projection * modelview * vec4(transform_vec3(ray_position), 1.0);
        f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
        gl_FragDepth = min(depth, (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5);
    } else {
        output_color = vec4(0.0);
    }
    return;

    // ray tracing here... hmm... not super stable
//    vec3 ray_origin = ray_position; // should this be p0, camera instead?
//    float t_start = min(t_points[0], t_points[1]);
//    float t_end = max(t_points[0], t_points[1]);
//    float n_samples = 4.0;
//    float dt = (t_end - t_start)/n_samples;
//    float current_t = t_start;
////    bool ever_sampled = false;
//    bool sampled;
//    vec3 tex_curr_pos;
////    vec4 v_clip_coord;
////    float f_ndc_depth;
////    float depth = 1.0;
//    while (current_t <= t_end ){
//        ray_position = ray_position_to_native_coords(current_t, p0, dir);
//        tex_curr_pos = (ray_position - left_edge) / range;
////        if (tex_curr_pos[0] >0 && tex_curr_pos[1] > 0 && tex_curr_pos[2] >0){
//        tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;
//        sampled = sample_texture(tex_curr_pos, curr_color, 0.0, 0.0, vec3(0.0));
//
//            //        if (sampled) {
//            //            ever_sampled = true;
//            //            v_clip_coord = projection * modelview * vec4(transform_vec3(ray_position), 1.0);
//            //            f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
//            //            depth = min(depth, (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5);
//            //
//            //        }
////        }
//        current_t = current_t + dt;
//    }
//
//    output_color = cleanup_phase(curr_color, dir, t_start, t_end);

//    if (ever_sampled) {
//        gl_FragDepth = depth;
//    }


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
