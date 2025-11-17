in vec2 model_vertex; // position is in-plane coordinates
out vec2 UV;
uniform mat4 to_worldview; // homogenous projection matrix from in-plane to world

void main()
{
    // first get the vertex position in world coordinates from the in-plane coords
    vec4 world_vertex = to_worldview * vec4(model_vertex, 0., 1.0);

    // calculate and return the final screen view position
    gl_Position = projection * modelview * world_vertex;

    // our in-plane coordinates ARE the texture coordinates, just pass those out
    UV = model_vertex;
}
