
flat in vec4 v_model;
flat in float field_value;
out vec4 color;
in vec2 UV;

void main(){
    float h2 = clamp(length(UV) * length(UV), 0.0, 1.0);
    float factor = texture(cm_tex, h2).r;
    color = vec4(factor * field_value);
}