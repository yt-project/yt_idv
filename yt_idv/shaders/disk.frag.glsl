
flat in vec4 v_model;
flat in float field_value;
out vec4 color;
in vec2 UV;

void main(){
    //color = vec4(field_value * float(length(UV) < 1.0));
    color = vec4(field_value);
    color.a = 1.0;
}