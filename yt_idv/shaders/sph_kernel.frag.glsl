
flat in vec4 v_model;
flat in float field_value;
flat in float column_weight;
out vec4 color;
in vec2 UV;

void main(){
    float h2 = clamp(length(UV) * length(UV), 0.0, 1.0);
    float factor = texture(cm_tex, h2).r;
    color = vec4(factor * field_value * column_weight);
    color.a = float(dot(UV, UV) < 1.0); // inside the circle
}
