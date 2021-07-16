=====
Usage
=====

``yt_idv`` can be instantiated for onscreen or offscreen rendering.
Unfortunately, each of these two engines conducts some startup processes that
make it impossible (or at the very least, beyond the capabilities of the
``yt_idv`` developers) to switch between them in a single session.

The three rendering methods at present are:

 * ``pyglet`` - this method utilizes `pyglet <https://pyglet.org/>`_ to draw windows, respond to events, and manage OpenGL contexts.  Drawing is still done using PyOpenGL.
 * ``EGL`` - this method utilizes `EGL <https://en.wikipedia.org/wiki/EGL_(API)>`_ via `PyOpenGL <https://pypi.org/project/PyOpenGL/>`_.  This is useful for *offscreen* rendering, for instance when running on a cluster node that has access to graphics acceleration, but which does not provide GUI access.
 * ``OSMesa`` - this method utilizes `OSMesa <https://docs.mesa3d.org/osmesa.html>`_ via `PyOpenGL <https://pypi.org/project/PyOpenGL/>`_.  This is useful for *offscreen* rendering when GPUs are not available on the rendering node.  It is a good fallback for when you can't use EGL.

These two methods are wrapped by the function :func:`yt_idv.render_context` function, which accepts its first argument as either the string ``egl``, ``osmesa`` or ``pyglet``.

-------------------
Interactive Windows
-------------------

To set up a window for interactive exploration, you can use the ``pyglet``
context.  The most straightforward way of setting up a window that allows for interactive exploration is to utilize a set of commands such as this::

    import yt
    import yt_idv

    ds = yt.load_sample("IsolatedGalaxy")
    rc = yt_idv.render_context()
    rc.add_scene(ds, "density")
    rc.run()

This will utilize a number of defaults, including that the scene contains only
the volume rendering of grid data, managed by a trackball camera.  By default,
a simple interface is added to the scene to provide some degree of control over
the display parameters.

.. note:: By default, the "engine" keyword argument to ``render_context`` is
          set to ``pyglet``.  So if you want to supply positional arguments,
          you have to also specify that as the first, or utilize all keyword
          arguments.

The key part of this is the ``rc.run()`` command; this removes control from the
user and creates a new Pylget "application" that handles all control from that
point.  If you are running this from a standard python interpreter, you need to
make any and all setup changes you want before this is called.

--------------------------
Interactivity with IPython
--------------------------

IPython provides the ability to work with Pyglet's threading model so that you
can access and modify objects while the rendering is interactive and ongoing.

.. warning:: This brings with it some serious performance penalties!  It often
             leads to lower framerates and higher-latency response to input
             events.

To utilize IPython in this way, you can start it with the command line option
``--gui=pyglet``.  For instance, you could execute the script above inline
after starting IPython in this way, or you can put those commands in a script
(``ytidv.py`` for instance) and execute it using ``ipython -i --gui=pyglet
ytidv.py`` and you will be presented with both the interactive window and an
interactive prompt where modifications to the scene and its components can be
made.

--------------------
Off-screen Rendering
--------------------

To utilize off-screen rendering, you can request either the "egl" or "osmesa"
render context::

    import yt
    import yt_idv

    ds = yt.load_sample("IsolatedGalaxy")
    rc = yt_idv.render_context("egl", width = 1024, height = 1024)
    rc.add_scene(ds, "density")
    image = rc.run()
    yt.write_bitmap(image, "idv.png")

Here, we load up the dataset, create a default scene, render it without a
window, and output the results.  When ``rc.run()`` is called, it returns an
image array, which we then supply to ``yt.write_bitmap``.

This seems a bit clunky, right?  Having to save the image?  Well, if you're
running in something that can render ipywidgets (such as Jupyter lab or a
Jupyter notebook) you can create an auto-updating image widget::

    rc.add_image()

This will return an image widget, which is then associated with the render
context.  Whenever ``rc.run()`` is called next, the image widget will update.

.. note:: Only the most recent image widget is retained!  So, if you call
          ``add_image`` multiple times, the new ones will be updated but the
          old ones will be frozen in time, like a bug stuck in amber.

This is useful if, for instance, you modify the position or focal point of the
camera, the bounds of the image, annotations, and so forth.

You can also have the render context run *and* output an image simultaneously
by using the ``rc.snap()`` function::

    rc.snap()

It will use a default template, and track how many snapshots have been made, but you can also supply a format string to it to output.

----------------------
Snapshots into a Movie
----------------------

If you want to turn your snapshots into a movie (x264 in mkv), this command (requires ``mencoder``) is a quick way to do it::

    mencoder mf://"snap*.png" -oac copy -of lavf -ovc x264 -x264encopts preset=veryslow:tune=film:crf=15:frameref=15:fast_pskip=0:global_header:threads=auto -o output_video.mkv
