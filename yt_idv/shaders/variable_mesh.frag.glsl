flat in vec4 v_model;
flat in float field_value;
out vec4 output_color;

void main()
{
    output_color = vec4(field_value);
}
