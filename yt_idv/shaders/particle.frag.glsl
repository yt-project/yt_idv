
flat in vec4 v_model;
flat in float field_value;
out vec4 color;

void main(){
    float d = distance(gl_PointCoord, vec2(0.5, 0.5));
    if (d > 0.5) discard;
    color = vec4(field_value, field_value, field_value, field_value);
}