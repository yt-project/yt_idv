
flat in vec4 v_model;
flat in float field_value;
out vec4 color;
varying in vec2 UV;

void main(){
    float d = distance(UV, vec2(0.0));
    if (d > 1.0) discard;
    color = vec4(field_value);
}