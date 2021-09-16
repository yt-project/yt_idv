in vec4 model_vertex;
in vec3 position_field; // The location of the vertex in model space
in vec3 width_field;
in float color_field;

flat out vec4 vradius;
flat out mat4 inverse_proj;
flat out mat4 inverse_mvm;
flat out mat4 inverse_pmvm;
flat out float field_value;
flat out vec4 v_model;

out vec2 UV;

void main()
{
    vec3 v1, v2, v3;
    v1 = disk_normal;
    ortho_find(v1, v2, v3);
    vec3 disk_position = position_field - disk_center;
    float r = distance(disk_center, position_field);
    float theta = atan(disk_position.y, disk_position.x) + PI;
    float phi = acos(disk_position.z / r);

    if ((r > r_bounds.y) || (r < r_bounds.x)
        || (theta > theta_bounds.y) || (theta < theta_bounds.x)
        || (phi > phi_bounds.y) || (phi < phi_bounds.x)) {
        vradius = vec4(0.0);
    } else {
        vradius = vec4(width_field, 1.0);
    }

    v_model = vec4(position_field, 1.0) + vradius * (model_vertex - 0.5);
    vec4 clip_pos = projection * modelview * v_model;
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

    //mat3 rotation = mat3(v1, v2, v3);
    disk_position = (v_model.xyz - disk_center);
    r = length(cross(disk_normal, disk_position));
    theta = atan(dot(v3, disk_position), dot(v2, disk_position)) + PI;
    phi = acos(dot(v1, disk_position) / r);

    gl_Position = vec4(r * cos(theta), r * sin(theta), 1, 1);
    UV = model_vertex.xy;
}
