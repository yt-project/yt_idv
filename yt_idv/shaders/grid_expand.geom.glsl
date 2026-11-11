layout ( points ) in;
layout ( triangle_strip, max_vertices = 14 ) out;

flat in vec3 vdx[];
flat in vec3 vleft_edge[];
flat in vec3 vright_edge[];

#ifdef SPHERICAL_GEOM
flat in vec3 vleft_edge_cart[];
flat in vec3 vright_edge_cart[];
flat in vec3 vdx_cart[];
flat out vec3 left_edge_cart;
flat out vec3 right_edge_cart;
flat out vec3 dx_cart;
#endif

flat out vec3 dx;
flat out vec3 left_edge;
flat out vec3 right_edge;

flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
out vec4 v_model;

flat in mat4 vinverse_proj[];
flat in mat4 vinverse_mvm[];
flat in mat4 vinverse_pmvm[];
flat in vec4 vv_model[];

flat in ivec3 vdata_offset[];
flat in ivec3 vdata_size[];
flat in ivec3 vbitmap_offset[];
flat in ivec3 vbitmap_size[];
flat out ivec3 data_offset;
flat out ivec3 data_size;
flat out ivec3 bitmap_offset;
flat out ivec3 bitmap_size;

// https://stackoverflow.com/questions/28375338/cube-using-single-gl-triangle-strip
// suggests that the triangle strip we want for the cube is

uniform vec3 arrangement[8] = vec3[](
    vec3(0, 0, 0),
    vec3(1, 0, 0),
    vec3(0, 1, 0),
    vec3(1, 1, 0),
    vec3(0, 0, 1),
    vec3(1, 0, 1),
    vec3(0, 1, 1),
    vec3(1, 1, 1)
);

uniform int aindex[14] = int[](6, 7, 4, 5, 1, 7, 3, 6, 2, 4, 0, 1, 2, 3);


void set_block_outputs(vec4 model_pos)
{
    left_edge = vleft_edge[0];
    right_edge = vright_edge[0];
    inverse_pmvm = vinverse_pmvm[0];
    inverse_proj = vinverse_proj[0];
    inverse_mvm = vinverse_mvm[0];

    #ifdef NONCARTESIAN_GEOM
    left_edge_cart = vleft_edge_cart[0];
    right_edge_cart = vright_edge_cart[0];
    dx_cart = vdx_cart[0];
    #endif

    dx = vdx[0];
    v_model = model_pos;
    data_offset = vdata_offset[0];
    data_size = vdata_size[0];
    bitmap_offset = vbitmap_offset[0];
    bitmap_size = vbitmap_size[0];
}

void emit_tile_quad(ivec2 tile_lo, ivec2 tile_hi, ivec2 ntiles, float ndc_z,
                    vec4 model_pos)
{
    // tiles split the screen at pixel (i * width) / ntiles, as in ray_table.py
    ivec2 size = textureSize(ray_table_tex, 0);
    vec2 lo = vec2((tile_lo * size) / ntiles) / vec2(size) * 2.0 - 1.0;
    vec2 hi = vec2((tile_hi * size) / ntiles) / vec2(size) * 2.0 - 1.0;
    vec2 corners[4] = vec2[](lo, vec2(hi.x, lo.y), vec2(lo.x, hi.y), hi);
    for (int i = 0; i < 4; i++) {
        gl_Position = vec4(corners[i], ndc_z, 1.0);
        set_block_outputs(model_pos);
        EmitVertex();
    }
    EndPrimitive();
}

void emit_ray_table_footprint(vec3 le, vec3 width)
{
    // A ray table has no projection to push the box through, so cover the
    // screen tiles whose cone of rays can reach the block's bounding sphere,
    // grown by how far any ray starts from the camera.
    vec4 center = vec4(le + 0.5 * width, 1.0);
    float radius = 0.5 * length(width) + (use_ray_origins > 0.5 ? ray_origin_spread : 0.0);
    vec3 v = (modelview * center).xyz;
    float dist = length(v);
    ivec2 ntiles = textureSize(ray_tile_tex, 0);
    float ndc_z = 2.0 * clamp((dist - radius) / far_plane, 0.0, 1.0) - 1.0;

    if (dist <= radius) {
        emit_tile_quad(ivec2(0), ntiles, ntiles, ndc_z, center);
        return;
    }

    vec3 vn = v / dist;
    float spread = asin(radius / dist);
    uint cols = 0u;  // ray_table.py keeps ntiles.x <= 32
    int row_lo = ntiles.y;
    int row_hi = -1;
    for (int ty = 0; ty < ntiles.y; ty++) {
        for (int tx = 0; tx < ntiles.x; tx++) {
            vec4 cone = texelFetch(ray_tile_tex, ivec2(tx, ty), 0);
            if (cone.w < 0.0) continue;
            float limit = cone.w + spread;
            if (limit < PI && dot(vn, cone.xyz) < cos(limit)) continue;
            cols |= 1u << uint(tx);
            row_lo = min(row_lo, ty);
            row_hi = max(row_hi, ty);
        }
    }
    if (cols == 0u) return;

    // Cover the hit columns with one span, or two where the shortest span
    // wraps around the screen edge (a panorama's seam): skip the longest
    // circular run of empty columns.
    int n = ntiles.x;
    int run = 0;
    int gap_len = 0;
    int gap_end = 0;
    for (int k = 0; k < 2 * n; k++) {
        if ((cols & (1u << uint(k % n))) == 0u) {
            run++;
            if (run > gap_len && run <= n) {
                gap_len = run;
                gap_end = k;
            }
        } else {
            run = 0;
        }
    }
    int start = (gap_end + 1) % n;
    int len = n - gap_len;
    if (gap_len == 0) {
        start = 0;
        len = n;
    }
    if (start + len <= n) {
        emit_tile_quad(ivec2(start, row_lo), ivec2(start + len, row_hi + 1),
                       ntiles, ndc_z, center);
    } else {
        emit_tile_quad(ivec2(start, row_lo), ivec2(n, row_hi + 1),
                       ntiles, ndc_z, center);
        emit_tile_quad(ivec2(0, row_lo), ivec2(start + len - n, row_hi + 1),
                       ntiles, ndc_z, center);
    }
}

void main() {

    vec4 center = gl_in[0].gl_Position;
    vec3 width, le;
    vec4 newPos;

    #ifdef NONCARTESIAN_GEOM
    width = vright_edge_cart[0] - vleft_edge_cart[0];
    le = vleft_edge_cart[0];
    #else
    width = vright_edge[0] - vleft_edge[0];
    le = vleft_edge[0];
    #endif

    if (projection_type == 2) {
        emit_ray_table_footprint(le, width);
        return;
    }

    for (int i = 0; i < 14; i++) {
        // walks through each vertex of the triangle strip, emit it. need to
        // emit gl_Position in cartesian, pass along other attributes in native
        // coordinates

        newPos = vec4(le + width * arrangement[aindex[i]], 1.0);
        gl_Position = projection * modelview * newPos;
        set_block_outputs(newPos);
        EmitVertex();
    }

}
