flat in vec4 v_model;
flat in float field_value;
out vec4 color;
in vec2 UV;

void main(){
    if (dot(UV, UV) >= 1.0) discard;
    color = vec4(vec3(field_value), 1.0);
}
