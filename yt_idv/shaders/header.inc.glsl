#version 330 core

const float INFINITY = 1. / 0.;
const float PI = 3.1415926535897932384626433832795;

// Fraction of the coordinate scale by which bounding box tests are padded.
// A ray position that lands on a face shared by two blocks is reconstructed
// slightly differently by each of them in float32, so an exact test can place
// the point outside both blocks and leave the pixel undrawn.
const float BBOX_TOL = 1e-5;

bool within_bb(vec3 pos, vec3 left_edge, vec3 right_edge)
{
    // the float32 error in pos comes from arithmetic on the coordinates
    // themselves, so it scales with their magnitude and not with the cell size
    vec3 tol = BBOX_TOL * max(abs(left_edge), abs(right_edge));
    bvec3 left =  greaterThanEqual(pos, left_edge - tol);
    bvec3 right = lessThanEqual(pos, right_edge + tol);
    return all(left) && all(right);
}
