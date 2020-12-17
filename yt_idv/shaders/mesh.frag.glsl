in float fragment_data;
out vec4 output_color;

void main()
{
    output_color = vec4(fragment_data);
    output_color.a = 1.0;
}
