in float px;
in float py;
in float pdx;
in float pdy;
in float field_value;

flat out vec4 vv_model;
flat out float vv_field_value;

void main()
{
    vv_model = vec4(px, py, pdx, pdy);
    vv_field_value = field_value;
    gl_Position = vec4(px, py, 0.0, 0.0);
}
