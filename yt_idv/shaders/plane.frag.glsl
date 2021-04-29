out vec4 output_color;
in vec2 UV;  // our in-plane coordinates

void main()
{
    float val = texture(fb_tex, UV).r;
    gl_FragDepth = 0.0;
    if(val == 0) discard;
    output_color = vec4(val);
}

