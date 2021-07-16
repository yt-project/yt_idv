flat in vec3 dx;
flat in vec3 left_edge;
flat in vec3 right_edge;
flat in mat4 inverse_proj;
flat in mat4 inverse_mvm;
flat in mat4 inverse_pmvm;
out vec4 output_color;
in vec4 v_model;

void main()
{
    vec3 ray_position = v_model.xyz;

    vec3 dist = min(abs(ray_position - right_edge),
                    abs(ray_position - left_edge));

    // We need to be close to more than one edge.

    int count = 0;
    count += int(dist.x < box_width * dx.x);
    count += int(dist.y < box_width * dx.y);
    count += int(dist.z < box_width * dx.z);

    if (count < 2) {
        discard;
    }

    output_color = vec4(box_color, box_alpha);

    //vec4 v_clip_coord = projection * modelview * vec4(ray_position, 1.0);
    vec4 v_clip_coord = projection * modelview * vec4(ray_position, 1.0);
    float f_ndc_depth = v_clip_coord.z / v_clip_coord.w;
    float depth = (1.0 - 0.0) * 0.5 * f_ndc_depth + (1.0 + 0.0) * 0.5;

    gl_FragDepth = depth;
}
