#version 330 core

const float INFINITY = 1. / 0.;
const float PI = 3.1415926535897932384626433832795;

// Fraction of the coordinate scale by which bounding box tests are padded.
// A ray position that lands on a face shared by two blocks is reconstructed
// slightly differently by each of them in float32, so an exact test can place
// the point outside both blocks and leave the pixel undrawn.
const float BBOX_TOL = 1e-5;

bool within_bb(vec3 pos, vec3 left_edge, vec3 right_edge)
{
    // the float32 error in pos comes from arithmetic on the coordinates
    // themselves, so it scales with their magnitude and not with the cell size
    vec3 tol = BBOX_TOL * max(abs(left_edge), abs(right_edge));
    bvec3 left =  greaterThanEqual(pos, left_edge - tol);
    bvec3 right = lessThanEqual(pos, right_edge + tol);
    return all(left) && all(right);
}

// Camera uniforms declared here rather than in known_uniforms.inc.glsl because
// get_ray_origin_and_dir below needs them and the header is concatenated first
uniform vec3 camera_pos;
uniform vec3 camera_view_dir; // normalize(focus - position)
uniform int projection_type;  // 0 = perspective (default), 1 = orthographic

// Sets the origin and direction of the ray to march so that along-ray
// distance, t, means is the distance in front of the camera
void get_ray_origin_and_dir(in vec3 ray_position, out vec3 ray_origin, out vec3 dir)
{
    if (projection_type == 1) {
        // orthographic: all rays are parallel to the view direction.
        dir = camera_view_dir;
        ray_origin = ray_position - dir * dot(ray_position - camera_pos.xyz, dir);
    } else {
        dir = -normalize(camera_pos.xyz - ray_position);
        ray_origin = camera_pos.xyz;
    }
    // clamp components away from zero; sign(0.0) == 0.0 would leave them
    // zero (idir = inf).
    vec3 dsign = sign(dir);
    dsign += vec3(equal(dsign, vec3(0.0)));
    dir = max(abs(dir), 0.0001) * dsign;
}
