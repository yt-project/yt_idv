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

// Slicing
uniform vec3 slice_position;
uniform vec3 slice_normal;

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
uniform sampler3D ds_tex[6];

// ray tracing control
uniform float sample_factor;

// external depth clip -- lets a ray's integration be stopped early at a
// per-pixel max window-space depth supplied by the caller (e.g. an opaque
// occluder rendered elsewhere), rather than always integrating out to the
// block's own bounding-box exit. use_external_depth_clip == 0 disables it
// (external_depth_tex is not sampled/read in that case). Added for
// cycles-volume-override's yt_idv integration -- see ray_tracing.frag.glsl.
uniform sampler2D external_depth_tex;
uniform float use_external_depth_clip;

// curve drawing control
uniform vec4 curve_rgba;

// isocontour control
uniform int iso_num_layers;
uniform float iso_layers[32];
uniform float iso_layer_tol[32];
uniform float iso_alphas[32];

// spherical coordinates
uniform int id_theta;  // azimuthal angle (0 to pi) index in the yt dataset
uniform int id_r;  // radial index in the yt dataset
uniform int id_phi;  // polar angle (0 to 2pi) indexi n the yt dataset

// draw outline control
uniform float draw_boundary;
uniform vec4 boundary_color;
