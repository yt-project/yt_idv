
flat in vec4 v_model;
flat in float field_value;
out vec4 color;
in vec2 UV;

void main(){
    float h2 = length(UV) * length(UV);
    float factor = texture(cm_tex, h2).r;
    color = vec4(factor * field_value);
}