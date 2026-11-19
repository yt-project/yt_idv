
flat in vec4 v_model;
flat in float field_value;
flat in float column_weight;
out vec4 color;
in vec2 UV;

void main(){
    float q2 = dot(UV, UV);
    if (q2 >= 1.0) discard;
    float factor = texture(cm_tex, q2).r;
    color = vec4(vec3(factor * field_value * column_weight), 1.0);
}
