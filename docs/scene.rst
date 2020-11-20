=====================
Controlling the Scene
=====================

The scene in ``yt_idv`` is made up of several components, all of which are
managed via objects possessing traitlets.

At the top most level, there is the :class:`yt_idv.scene_graph.SceneGraph`
object, which usually lives on a rendering context as the ``scene`` attribute.
This class, which is riddled with traitlets, manages the drawing of all of the
different visualization components and annotations.

There are three types of objects that the ``SceneGraph`` manages:

 * ``annotations`` -- These are subclasses of
   :class:`~yt_idv.scene_annotations.base_annotation.SceneAnnotation` and are
   generally rendered with only one type of shader.  This includes things like
   a text annotation and box outlines.
 * ``components`` -- These are subclasses of
   :class:`~yt_idv.scene_components.base_component.SceneComponent` and are data
   visualization components.  This includes block rendering and mesh rendering,
   and may at some point be expanded to include particle rendering.
 * ``data_objects`` -- These are subclasses of
   :class:`~yt_idv.scene_data.base_data.SceneData`.  Some types of data can be
   reused and shared between components and annotations.  These objects manage
   data that needs to be stored on the GPU.  For instance, this includes 3D
   textures that correspond to the block data and the vectors that define the
   coordinates of the grid edges, as well as font glyph information.

Each of these objects has a set of attributes that define its appearance and
how it is drawn.  These attributes can be changed with either programmatic
access of by accessing them in the GUI.

In addition to these, the scene also possesses:

 * ``camera`` -- at present, this is always an instance of
   :class:`~yt_idv.cameras.trackball_camera.TrackballCamera`.  It controls the
   orientation and position of the viewpoint, as well as its field of view.
 * ``image`` -- this will read the image back and return it as a 4-component,
   2D floating point array.

----------------
Volume Rendering
----------------

A volume rendering component can be added to a scene by calling
:meth:`~yt_idv.scene_graph.SceneGraph.add_volume`.

The volume rendering in ``yt_idv`` is similarly implemented to the software
volume rendering in yt itself.  It utilizes a kdtree decomposition of the
source data object to construct 3D textures that reside on the graphics card,
and then conducts a front-to-back evaluation of them in order.

The data that lives on the GPU is a
:class:`~yt_idv.scene_data.block_collection.BlockCollection`.  This contains, for
each "block," a 3D texture of the data field to render and a 3D texture of the
bitmap of included points.  (Future versions of ``yt_idv`` will endeavor to
make it easier to modify these bitmaps to perform selections.)

The rendering component is an instance of
:class:`~yt_idv.scene_components.blocks.BlockRendering`.  This has several
properties that are likely of interest for controlling the rendering.
Modifying these will update the rendering the next time a frame is rendered.
It is worth noting that because we are using traitlets validation, even though
some of these are backed by OpenGL-specific values, they often will
automatically convert data.  For instance, the ``colormap`` property will
convert a string to the appropriate texture on the GPU.

* ``render_method`` -- this is a string that changes the fragment shaders used
  to render the blocks.  For a volume rendering component, this can be
  ``"projection"``, ``"max_intensity"`` or ``"transfer_function"``.
* ``colormap`` -- setting this to a string will change the colormap to that
  matplotlib colormap.  This only has effect if using ``"projection"`` or
  ``"max_intensity"``.
* ``cmap_min`` and ``cmap_max`` -- these are floating point values for the
  colormap bounds.  If either or both are set to None, the colormap will be
  dynamically .
* ``cmap_log`` -- a bool governing whether or not the values should be logged
  before the colormap is applied.
* ``transfer_function`` -- this is an instance of a special class of 2D texture
  that has RGBA channels.  You can access or modify its ``data`` attribute to
  change the transfer function values.  This only has impact if you are using
  the ``render_method`` of ``"transfer_function"``.

Boxes can also be added as an annotation to show the 3D textures being rendered
by a :class:`~yt_idv.scene_components.BlockRendering`.  This will re-use the
underlying :class:`~yt_idv.scene_data.block_collection.BlockCollection`, and
can be added by manually constructing an annotation:

.. code-block:: python

   from yt_idv.scene_annotations.block_outline import BlockOutline

   rc.add_scene(dd, "density")
   block_data = rc.data_objects[0]
   rc.scene.annotations.append(BlockOutline(data = block_data))

The block outlines here will match the textures rendered, which will likely be
different from the underlying grid structure.

----------------
Text Annotations
----------------

Text annotations can be added to a scene by calling
:meth:`~yt_idv.scene_graph.SceneGraph.add_text`.  This will utilize a (default)
set of font glyphs (in "DejaVu Sans") to display text.  It is also possible to
construct an alternate instance of
:class:`~yt_idv.scene_data.text_characters.TextCharacters` with a different
font, and specify that as ``data`` to the ``add_text`` call.

The instance of :class:`~yt_idv.scene_annotations.text.TextAnnotation` that
provides the actual annotation has several properties that are of interest in
changing its appearance.

* ``text`` -- this is the unicode string displayed.  Changing this will update
  the draw instructions and thus the annotation.
* ``origin`` -- this is a tuple of floats, each of which are between -1 and 1,
  for the origin (bottom left) to display the text.  This is in screen
  coordinates, where (-1, -1) is the lower left corner of the screen.
* ``scale`` -- the multiplicative factor for the size of the text.

An annotation such as this can be used for displaying captions, time, etc.

---------------
Box Annotations
---------------

Box annotations can be added to a scene by calling
:meth:`~yt_idv.scene_graph.SceneGraph.add_box`.  This accepts a set of corners
for the min (i.e., "left") and the max (i.e., "right") edges of the box.  The
attributes that might be of interest to control the rendering are:

* ``box_width`` -- this float governs the width of the lines that are drawn.
  This is in coordinate space of the domain, rather than the screen.  *
* ``box_alpha`` -- this float is the opacity of the boxes.  It ranges from 0.0
  to 1.0.

--------------
Camera Control
--------------

Each scene has an instance of a
:class:`~yt_idv.cameras.trackball_camera.TrackballCamera` object.  (Other
cameras may be implemented in the future, but for now, everything is this.)

This has a set of parameters that allow you to change its position and
direction.

.. note:: One interesting thing is that the projection matrix used here is
          identical to the projection matrix used by pythreejs, which means
          it's possible to link the two up!

* ``position`` -- this is the position of the camera
* ``focus`` -- what point (in data coordinates) is the camera looking at?
* ``up`` -- this vector is the vector corresponding to "up" in the scene
* ``fov`` -- this floating point value controls the field of view.  By default
  this is 45.
* ``near_plane`` and ``far_plane`` -- these control the near/far values input
  into the projection matrix.  The important quantity here is their ratio; by
  default we allow for a 2e4 ratio.

In general, it's tricky to get the position of the camera just right, and there
are also a number of properties of it that are not properly exposed.  This is
an area of future improvement in ``yt_idv``, especially for things like
automating "nice" camera motion between points and viewing directions.
