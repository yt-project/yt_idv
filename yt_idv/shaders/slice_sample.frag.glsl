in vec4 v_model;
flat in vec3 dx;
flat in vec3 left_edge;
flat in vec3 right_edge;
flat in mat4 inverse_proj;
flat in mat4 inverse_mvm;
flat in mat4 inverse_pmvm;
out vec4 output_color;

bool sample_texture(vec3 tex_curr_pos, inout vec4 curr_color, float tdelta,
                    float t, vec3 dir);
vec4 cleanup_phase(in vec4 curr_color, in vec3 dir, in float t0, in float t1);

// This main() function will call a function called sample_texture at every
// step along the ray.  It must be of the form
//   void (vec3 tex_curr_pos, inout vec4 curr_color, float tdelta, float t,
//         vec3 direction);

void main()
{
    // the interpolated position on this block's face that the ray passes
    // through. un-projecting gl_FragCoord through inverse_pmvm gives the same
    // point in exact arithmetic, but with a small near plane that matrix is
    // badly conditioned and the float32 result is off by enough that two
    // blocks disagree about where a ray crosses the face they share.
    vec3 ray_position = v_model.xyz;

    // note: dir points toward the camera here, hence -camera_view_dir for
    // the parallel rays of an orthographic projection
    vec3 dir = (projection_type == 1)
        ? -camera_view_dir
        : normalize(camera_pos.xyz - ray_position);
    vec4 curr_color = vec4(0.0);

    // We'll compute the t at which this ray intersects the slice. If that t
    // results in a position that is within this box, we'll sample and return.
    // For a nice, rust-y walkthrough: https://samsymons.com/blog/math-notes-ray-plane-intersection/
    float t_intersect = dot((slice_position - ray_position), slice_normal) / dot(dir, slice_normal);
    // the ray runs parallel to the slice (or through it at a grazing angle
    // that overflows), so it never lands in this block
    if (isinf(t_intersect) || isnan(t_intersect)) discard;
    ray_position += t_intersect * dir;
    if (!within_bb(ray_position, left_edge, right_edge)) discard;

    vec3 range = (right_edge + dx/2.0) - (left_edge - dx/2.0);
    vec3 nzones = range / dx;
    vec3 ndx = 1.0/nzones;

    vec3 tex_curr_pos = (ray_position - left_edge) / range;  // Scale from 0 .. 1
    // But, we actually need it to be 0 + normalized dx/2 to 1 - normalized dx/2
    tex_curr_pos = (tex_curr_pos * (1.0 - ndx)) + ndx/2.0;

    float map_sample = texture(bitmap_tex, tex_curr_pos).r;
    if (!(map_sample > 0.0)) discard;

    output_color = texture(ds_tex[0], tex_curr_pos);
}
