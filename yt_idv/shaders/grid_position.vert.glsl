// note: all in/out variables below are always in native coordinates (e.g.,
// spherical or cartesian) except when noted.

in vec4 model_vertex;
in vec3 in_dx;
in vec3 in_left_edge;
in vec3 in_right_edge;



flat out vec4 vv_model;
flat out mat4 vinverse_proj;
flat out mat4 vinverse_mvm;
flat out mat4 vinverse_pmvm;
flat out vec3 vdx;
flat out vec3 vleft_edge;
flat out vec3 vright_edge;

// where the block lies in the data and bitmap atlases, see known_uniforms.inc.glsl
in ivec3 in_data_offset;
in ivec3 in_data_size;
in ivec3 in_bitmap_offset;
in ivec3 in_bitmap_size;
flat out ivec3 vdata_offset;
flat out ivec3 vdata_size;
flat out ivec3 vbitmap_offset;
flat out ivec3 vbitmap_size;

#ifdef NONCARTESIAN_GEOM
// pre-computed cartesian le, re
in vec3 le_cart;
in vec3 re_cart;
in vec3 dx_cart;

flat out vec3 vleft_edge_cart;
flat out vec3 vright_edge_cart;
flat out vec3 vdx_cart;
#endif


void main()
{
    vdata_offset = in_data_offset;
    vdata_size = in_data_size;
    vbitmap_offset = in_bitmap_offset;
    vbitmap_size = in_bitmap_size;

    // camera uniforms: projection, modelview
    vv_model = model_vertex;
    vinverse_proj = inverse(projection);

    // inverse model-view-matrix
    vinverse_mvm = inverse(modelview);
    vinverse_pmvm = inv_pmvm;
    gl_Position = projection * modelview * model_vertex;

    // native coordinates
    vdx = vec3(in_dx);
    vleft_edge = vec3(in_left_edge);
    vright_edge = vec3(in_right_edge);

    #ifdef NONCARTESIAN_GEOM
    // cartesian bounding boxes
    vleft_edge_cart = vec3(le_cart);
    vright_edge_cart = vec3(re_cart);
    vdx_cart = vec3(dx_cart);
    #endif
}
