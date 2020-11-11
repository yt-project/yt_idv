=====
Usage
=====

``yt_idv`` can be instantiated for onscreen or offscreen rendering.
Unfortunately, each of these two engines conducts some startup processes that
make it impossible (or at the very least, beyond the capabilities of the
``yt_idv`` developers) to switch between them in a single session.

The two rendering methods at present are:

 * ``pyglet`` - this method utilizes `pyglet<https://pyglet.org/>`_ to draw windows, respond to events, and manage OpenGL contexts.  Drawing is still done using PyOpenGL.
 * ``EGL`` - this method utilizes `EGL<https://en.wikipedia.org/wiki/EGL_(API)>`_ via `PyOpenGL<https://pypi.org/project/PyOpenGL/>`_.  This is useful for *offscreen* rendering, for instance when running on a cluster node that has access to graphics acceleration, but which does not provide GUI access.

These two methods are wrapped by the function :func:`yt_idv.render_context` function, which accepts its first argument as either the string ``egl`` or ``pyglet``.

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

To utilize off-screen rendering, you can request the "egl" render context::

    import yt
    import yt_idv

    ds = yt.load_sample("IsolatedGalaxy")
    dd = ds.all_data()

    rc = yt_idv.render_context("egl", width = 1024, height = 1024)
    rc.add_scene(dd, "density")

    image = rc.run()
    yt.write_bitmap(image, "idv.png")

Here, we load up the dataset, create a default scene, render it without a
window, and output the results.  When ``rc.run()`` is called, it returns an
image array, which we then supply to ``yt.write_bitmap``.


