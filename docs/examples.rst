========
Examples
========

----------------------------
Interactive Volume Rendering
----------------------------

This is a simple script for loading the ``IsolatedGalaxy`` example dataset and creating an interactive rendering window for it, including a GUI.

.. literalinclude:: ../examples/amr_volume_rendering.py
   :language: python
   :linenos:

---------------------------
Off-screen Volume Rendering
---------------------------

This is a simple script for loading the ``IsolatedGalaxy`` example dataset,
creating an off-screen rendering context, and then taking two snapshots.

.. literalinclude:: ../examples/amr_offscreen.py
   :language: python
   :linenos:

-------------------
Making a Zoom Movie
-------------------

This script loads the ``HiresIsolatedGalaxy`` sample dataset, creates a
1024x1024 offscreen rendering context, sets the camera position and then zooms
toward the center, making 400 snapshots.  It also sets the ``cmap_min`` and
``cmap_max`` attributes, so the colormap is allowed to be dynamically set at
every step.

.. literalinclude:: ../examples/hires_galaxy.py
   :language: python
   :linenos:

-----------------------------
Interactive Widget in Jupyter
-----------------------------

This script, when executed as a series of Jupyter notebook cells, will create
an off-screen context and render into that.  The call to
:meth:`~yt_idv.scene_graph.SceneGraph.add_image` will create an ``Image``
widget that is auto-updated when the scene runs.

.. code-block:: python
   :linenos:

   import yt
   import yt_idv

   ds = yt.load_sample("IsolatedGalaxy")
   dd = ds.all_data()

   rc = yt_idv.render_context("egl", width = 400, height = 400)
   rc.add_scene(dd, "density", no_ghost=True)
   rc.run()
   rc.add_image()

Note that if you have access to OSMesa but not EGL, you can use the OSMesa
rendering context instead.
