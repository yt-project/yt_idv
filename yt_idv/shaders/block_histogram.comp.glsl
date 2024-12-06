layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
layout(binding = 0) uniform sampler3D texData;
layout(binding = 1) uniform sampler3D bitmapData;
layout(r32i, binding = 2) uniform iimage1D uHistogram;

void main() {
      // Get thread identifiers within the work group
  uint gidX = gl_WorkGroupID.x;
  uint gidY = gl_WorkGroupID.y;
  uint gidZ = gl_WorkGroupID.z;
  ivec3 dims = textureSize(texData, 0);
  uint N = dims.x;
  uint NxM = dims.x * dims.y;
  uint NxMxL = dims.x * dims.y * dims.z;

  // Calculate global thread ID
  uint globalIdx = gidZ * gl_NumWorkGroups.y * gl_NumWorkGroups.x + gidY * gl_NumWorkGroups.x + gidX;
    // Check if global ID is within texture bounds
  if (globalIdx >= NxMxL) {
    return;
  }

  // Calculate 3D texture coordinates from global ID
  uint z = globalIdx / (NxM);
  uint remainder = globalIdx % (NxM);
  uint y = remainder / N;
  uint x = remainder % N;

  // Sample the value from the 3D texture
  vec4 texValue = texture(texData, vec3(x, y, z));

  // Normalize the value to the range [0, 1] based on min and max
  float normalizedValue = (texValue.r - min_val) / (max_val - min_val);

  // Clamp the normalized value to [0, 1]
  normalizedValue = clamp(normalizedValue, 0.0, 1.0);

  // Calculate the bin index based on the number of bins
  int binIndex = int(normalizedValue * (bins - 1));

  imageAtomicAdd(uHistogram, binIndex, 1);

}