in vec2 model_vertex; // position in model space (in coordinates of the plane)
out vec2 UV;

uniform vec3 east_vec; // world coordinates of in-plane "y" basis vector
uniform vec3 north_vec; // world coordinates of in-plane "x" basis vector
uniform vec3 plane_pt; // world position of plane origin (with origin offset???)

void main()
{
    vec3 world_vertex = model_vertex[0] * east_vec + model_vertex[1] * north_vec + plane_pt;
    gl_Position = projection * modelview * vec4(world_vertex, 1.0);

    UV = model_vertex ; // we're actually passing in our texture coords already!!
}
