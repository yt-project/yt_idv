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
uniform int projection_type;  // 0 = perspective (default), 1 = orthographic, 2 = ray table
uniform mat4 modelview;
uniform mat4 projection;
uniform float far_plane;

// Ray table camera: one camera-space ray direction per pixel (zero where a
// pixel has no ray), and for each screen tile a cone (axis, half-angle in
// radians; negative for a tile with no rays) that holds all of its rays.
uniform sampler2D ray_table_tex;
uniform sampler2D ray_tile_tex;
// Optional ray origins: camera-space offsets from camera_pos, times
// ray_origin_scale; ray_origin_spread is the largest scaled offset.
uniform sampler2D ray_origin_tex;
uniform float use_ray_origins;
uniform float ray_origin_scale;
uniform float ray_origin_spread;

vec3 clamp_dir(vec3 dir)
{
    // clamp components away from zero; sign(0.0) == 0.0 would leave them
    // zero (idir = inf).
    vec3 dsign = sign(dir);
    dsign += vec3(equal(dsign, vec3(0.0)));
    return max(abs(dir), 0.0001) * dsign;
}

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
    dir = clamp_dir(dir);
}

// The ray table's ray through window position frag_xy (gl_FragCoord.xy), with
// viewport_xywh = (x, y, width, height); false if that pixel has no ray.
bool get_ray_table_ray(in vec2 frag_xy, in vec4 viewport_xywh,
                       out vec3 ray_origin, out vec3 dir)
{
    ivec2 size = textureSize(ray_table_tex, 0);
    vec2 frac = (frag_xy - viewport_xywh.xy) / viewport_xywh.zw;
    ivec2 texel = clamp(ivec2(frac * vec2(size)), ivec2(0), size - 1);
    vec3 cam_dir = texelFetch(ray_table_tex, texel, 0).xyz;
    ray_origin = camera_pos.xyz;
    dir = vec3(1.0);
    if (dot(cam_dir, cam_dir) < 1e-12) return false;
    // the view rotation is orthonormal: its transpose maps camera to model space
    mat3 camera_to_model = transpose(mat3(modelview));
    dir = clamp_dir(normalize(camera_to_model * cam_dir));
    if (use_ray_origins > 0.5) {
        vec3 offset = texelFetch(ray_origin_tex, texel, 0).xyz * ray_origin_scale;
        ray_origin += camera_to_model * offset;
    }
    return true;
}

// Window-space depth of a model-space point on a ray from ray_origin. Ray
// table cameras have no projection matrix, so their depth is the distance
// along the ray over far_plane.
float window_depth(vec3 p, vec3 ray_origin)
{
    if (projection_type == 2) {
        return clamp(length(p - ray_origin) / far_plane, 0.0, 1.0);
    }
    vec4 clip = projection * modelview * vec4(p, 1.0);
    return 0.5 * clip.z / clip.w + 0.5;
}
