in vec2 model_vertex;
in vec3 position_field; // The location of the vertex in model space
in vec3 width_field;
in float color_field;

flat out float vradius;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out float field_value;
flat out vec4 v_model;

out vec2 UV;

void main()
{
    v_model = vec4(position_field, 1.0);
    vec4 clip_pos = projection * modelview * v_model;
    vradius = width_field.x;
    inverse_pmvm = inv_pmvm;
    if (color_field == 0.0) {
        field_value = 1.0;
    } else {
        field_value = color_field;
    }

    // since we have theta: [0, 2pi) and phi: [0, pi] we use
    // r = sqrt(x^2 + y^2 + z^2)
    // theta = arctan(y/x)
    // phi = arccos(z/r)

    vec3 disk_position = position_field - disk_center;
    float r = distance(disk_center, position_field);
    float theta = atan(disk_position.y, disk_position.x) + PI;
    float phi = acos(disk_position.z / r);

    if ((r > r_bounds.y) || (r < r_bounds.x)
        || (theta > theta_bounds.y) || (theta < theta_bounds.x)
        || (phi > phi_bounds.y) || (phi < phi_bounds.x)) {
        vradius = 0.0;
    }

    vec2 leftCorner, rightCorner;

    leftCorner = (projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(-1.0, -1.0, clip_pos.zw)))).xy;
    rightCorner = (projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(1.0, 1.0, clip_pos.zw)))).xy;

    // Making radius zero will make our vertices degenerate and serve as a filter.
    gl_Position = projection * modelview * (v_model + vradius * normalize(inverse_pmvm * vec4(model_vertex, clip_pos.zw)));
    gl_Position.zw = clip_pos.zw;

    UV = model_vertex;
}
