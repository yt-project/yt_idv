
flat in vec4 v_model;
flat in float field_value;
out vec4 color;

void main(){
    color = vec4(field_value);
}