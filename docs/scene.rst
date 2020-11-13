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



----------------
Text Annotations
----------------



---------------
Box Annotations
---------------
