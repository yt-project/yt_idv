in vec2 model_vertex; // position in model space (in coordinates of the plane)
//in float vertex_data;
//out float fragment_data;
out vec2 UV;

uniform vec3 basis_v; // world coordinates of in-plane "y" basis vector
uniform vec3 basis_u; // world coordinates of in-plane "x" basis vector
uniform vec3 plane_pt; // world position of plane origin (with origin offset???)

void main()
{
    vec3 world_vertex = model_vertex[0] * basis_u + model_vertex[1] * basis_v + plane_pt;
    gl_Position = projection * modelview * vec4(world_vertex, 1.0);
//    fragment_data = vertex_data;

    UV = model_vertex ; // we're actually passing in our texture coords already!!
}
