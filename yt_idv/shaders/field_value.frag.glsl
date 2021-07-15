
flat in vec4 v_model;
flat in float field_value;
out vec4 color;
in vec2 UV;

void main(){
    color = vec4(float(length(UV) < 1.0));
}