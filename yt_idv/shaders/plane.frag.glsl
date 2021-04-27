//in float fragment_data;
out vec4 output_color;
in vec2 UV;  // our plane coordinates
void main()
{
//    output_color = vec4(fragment_data);
//    output_color.a = 1.0;

    float val = texture(fb_tex, UV).r;
    gl_FragDepth = 0.0;
    if(val == 0) discard;
    output_color = vec4(val);
}

