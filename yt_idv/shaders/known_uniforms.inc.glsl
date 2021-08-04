// Box annotation control
uniform float box_alpha;
uniform float box_width;
uniform vec3 box_color;

// Colormap control
uniform float cmap_log;
uniform float cmap_max;
uniform float cmap_min;

// Text and particle control
uniform float scale;
uniform float max_particle_size;
uniform float x_offset;
uniform float x_origin;
uniform float y_offset;
uniform float y_origin;

// Transfer function control
uniform float tf_log;
uniform float tf_max;
uniform float tf_min;

// Control of RGB channel information
uniform int channel;

// Mesh rendering
uniform mat4 model_to_clip;

// Matrices for projection and positions
uniform mat4 modelview;
uniform mat4 projection;
uniform vec3 camera_pos;
uniform vec4 viewport; // (offset_x, offset_y, 1 / screen_x, 1 / screen_y)
uniform mat4 inv_pmvm;
uniform float near_plane;
uniform float far_plane;

// textures we tend to use
uniform sampler1D cm_tex;
uniform sampler2D db_tex;
uniform sampler2D fb_tex;
uniform sampler2D tf_tex;
uniform sampler3D bitmap_tex;
uniform sampler3D ds_tex;

// ray tracing control
uniform float sample_factor;

// disk slice renderer
// in our convention, theta runs from 0 .. 2pi and phi from 0 .. pi
uniform vec3 disk_center;
uniform vec3 disk_vector;
uniform vec2 theta_bounds; 
uniform vec2 phi_bounds;
uniform vec2 r_bounds;

const float PI = 3.1415926535897932384626433832795;
const float PI_2 = 1.57079632679489661923;
const float PI_4 = 0.785398163397448309616;