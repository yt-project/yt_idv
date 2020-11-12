=====================
Controlling the Scene
=====================

The scene in ``yt_idv`` is made up of several components, all of which are
managed via objects possessing traitlets.

At the top most level, there is the :class:`yt_idv.scene_graph.SceneGraph`
object, which usually lives on a rendering context as the ``scene`` attribute.

