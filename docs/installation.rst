.. highlight:: shell

============
Installation
============


Stable release
--------------

To install yt_idv, run this command in your terminal:

.. code-block:: console

    $ pip install yt_idv

This is the preferred method to install yt_idv, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for yt_idv can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/yt-project/yt_idv

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/yt-project/yt_idv/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


Extra steps for linux
---------------------

A number of linux distros (Ubuntu 21+, Fedora 34+) have switched the default graphics backend from Xorg to Wayland.

To Use yt_idv on these linux distributions, you may need enforce Xorg usage, which you can do in several ways:

1. Log into an Xorg session. For Ubuntu, you can still select to launch an Xorg session on the login screen (see `here <https://askubuntu.com/a/961345>`_).

OR

2. Set the ``PYOPENGL_PLATFORM`` environment variable to ``"gdx"``.  In a bash shell:

.. code-block:: console

   $ export PYOPENGL_PLATFORM="gdx"

To avoid having to set this variable each time, you can add the above line to your ``.bashrc`` or ``.bash_aliases`` file.

See `Issue 81 <https://github.com/yt-project/yt_idv/issues/81>`_ for more information.


.. _headless-macos:

Extra steps for headless rendering on macOS
-------------------------------------------

Start by answering one question: **does the machine have a logged-in window
server session?**  It decides everything that follows.  Note that this is not the
same as having a monitor plugged in -- a Mac with no display attached but with
somebody logged in still has one.  Ask the machine:

.. code-block:: console

    $ launchctl managername
    Aqua

``Aqua`` means yes.  ``Background`` or ``StandardIO`` -- what you get over a bare
``ssh`` connection -- means no.

Yes -- use a hidden pyglet window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are rendering on your own Mac, or on any machine where somebody is logged
in graphically, do not reach for an off-screen engine at all.  A pyglet window
created with ``visible=False`` still gets a real Apple OpenGL context, which
means the GPU does the work::

    import yt
    import yt_idv

    rc = yt_idv.render_context(
        "pyglet", width=1024, height=1024, visible=False, gui=False
    )
    rc.add_scene(ds, "density", no_ghost=True)
    image = rc.run()
    yt.write_bitmap(image, "idv.png")

``rc.run()`` on a hidden window renders once and returns the image array, exactly
like the ``egl`` and ``osmesa`` contexts, rather than entering pyglet's event
loop.  ``rc.snap()`` and ``rc.add_image()`` work too.

This is by far the fastest option, and the only one that touches the GPU.  On an
M2 Max it reports ``GL_RENDERER = Apple M2 Max``, ``GL_VERSION = 4.1 Metal``, and
renders a 512x512 AMR volume in about 13 ms once warm -- against 90 ms for
OSMesa/llvmpipe and 4.8 s for EGL/softpipe.  Apple's OpenGL is deprecated and
capped at 4.1, but ``yt_idv``'s shaders are ``#version 330 core``, so that is
enough.

The catch is that Apple's OpenGL needs a window server connection.  Over a bare
``ssh`` session there is none, and this will not work.

No -- use Mesa's EGL
~~~~~~~~~~~~~~~~~~~~

For a machine with no GUI session at all, you are in software-rendering
territory, and the engine to use is ``egl``.

**OSMesa is a dead end on macOS.**  Mesa builds for macOS have stopped shipping
``libOSMesa``:

* conda-forge's ``mesalib`` ships ``libOSMesa.dylib`` on ``osx-arm64`` only up
  to and including **25.0.5**.  From 25.1 on, the package contains just
  ``libvulkan_lvp.dylib``, and 26.x is an empty metapackage that pulls in
  ``mesa-lavapipe`` and ``mesa-kosmickrisp`` (Vulkan drivers, no OpenGL).
* homebrew's ``mesa`` bottle drops ``libOSMesa`` as of 26.x, keeping ``libEGL``
  and ``libGL``.

So if you already have a working OSMesa environment, keep it and pin
``mesalib<=25.0.5``.  For anything new, use EGL.

**EGL is what remains.**  Install a Mesa that provides ``libEGL`` and
``libGL``:

.. code-block:: console

    $ brew install mesa

Then request the ``egl`` engine as usual::

    rc = yt_idv.render_context("egl", width=1024, height=1024)

``yt_idv`` handles the two macOS-specific wrinkles for you when it builds an EGL
context on darwin:

1. Mesa's EGL defaults to the X11 platform, which fails with
   ``EGL_NOT_INITIALIZED`` unless XQuartz is running.  ``yt_idv`` sets
   ``EGL_PLATFORM=surfaceless`` (only if you have not set it yourself), which is
   the platform that needs no display server.
2. PyOpenGL's EGL backend looks up its GL entry points by asking
   ``ctypes.util.find_library`` for ``"OpenGL"``, and on macOS that always
   resolves to Apple's ``OpenGL.framework`` rather than to Mesa's ``libGL`` --
   the library the EGL context actually belongs to.  Every GL call would then go
   to the wrong implementation.  ``yt_idv`` loads Mesa's ``libEGL.dylib`` and
   ``libGL.dylib`` by absolute path instead.

Mesa is searched for under ``$YT_IDV_MESA_PREFIX``, ``$CONDA_PREFIX``,
``/opt/homebrew``, ``/usr/local`` and ``/opt/local`` (in that order, checking
both ``lib/`` and ``opt/mesa/lib/``).  If yours lives somewhere else, point
``yt_idv`` at it:

.. code-block:: console

    $ export YT_IDV_MESA_PREFIX=/path/to/mesa   # contains lib/libEGL.dylib

Check which rasterizer you got -- this makes a very large difference::

    from OpenGL import GL
    print(GL.glGetString(GL.GL_RENDERER))

``llvmpipe`` is the fast software rasterizer and is what you want.  ``softpipe``
is the reference rasterizer and is roughly 50x slower (4.8 s versus 0.09 s for a
512x512 AMR volume render here).  You get ``softpipe`` when Mesa was built
without LLVM: homebrew's ``mesa`` 24.2.5 had no ``llvm`` dependency and its
``libgallium`` contains no ``llvmpipe`` at all, whereas the 26.2.1 bottle does.
If you land on ``softpipe``, upgrade Mesa.

See ``examples/headless_macos.py`` for a script covering both paths.

Why can't EGL use the GPU?
~~~~~~~~~~~~~~~~~~~~~~~~~~

The EGL path above is software rendering.  Note that ``brew upgrade mesa`` buys
you ``llvmpipe`` instead of ``softpipe`` -- a ~50x speedup, but still the CPU.
The only route to the GPU on macOS today is the hidden-window path above.

The tempting escape route is Mesa's ``zink`` (OpenGL implemented on top of
Vulkan) sitting on ``kosmickrisp`` (Vulkan implemented on top of Metal), which
would give a GPU-backed EGL context that needs no window server.  The pieces do
exist:

* conda-forge's ``mesa-kosmickrisp`` works.  With ``libvulkan-loader`` installed,
  ``vulkaninfo`` reports a real device (``deviceName = Apple M2 Max``,
  ``driverID = DRIVER_ID_MESA_KOSMICKRISP``).
* homebrew's ``libgallium`` contains ``zink``.

They do not currently meet.  ``conda install mesalib`` cannot supply the OpenGL
half at all -- on ``osx-arm64`` it installs only Vulkan ICDs
(``libvulkan_lvp.dylib``, ``libvulkan_kosmickrisp.dylib``) and no ``libEGL``,
``libGL``, ``libOSMesa`` or ``libgallium``.  Going the other way, with homebrew's
``libEGL`` and a conda Vulkan ICD, Mesa 24.2.5 refuses either way you ask:

* ``MESA_LOADER_DRIVER_OVERRIDE=zink`` is ignored -- the surfaceless platform
  logs ``Falling back to surfaceless swrast without DRM`` and hands back
  ``softpipe``.
* ``GALLIUM_DRIVER=zink`` is honored, and then ``eglInitialize`` fails outright
  with ``EGL_NOT_INITIALIZED`` / ``failed to create dri2 screen``, because zink
  is not a swrast driver and there is no DRM device to attach it to.
* ``EGL_PLATFORM=device`` segfaults.

Mesa 24.2.5's EGL also reports ``did not find extension DRI_Kopper``, and kopper
is the loader piece zink needs.  Mesa 26.x does ship it (``DRI_KopperLoader``,
``LIBGL_KOPPER_DISABLE``), so this may become possible -- but its surfaceless
platform still contains the same ``Falling back to surfaceless swrast without
DRM`` path, so do not count on it.  **This has not been tested against Mesa
26.x.**

None of these failures involve ``yt_idv``: they reproduce identically from a bare
``eglGetDisplay``/``eglInitialize`` pair with PyOpenGL alone, and the segfault is
inside Mesa's ``libEGL``.

ANGLE is not an alternative here: ``yt_idv``'s shaders are desktop GL
(``#version 330 core``) rather than GLES.

.. _Github repo: https://github.com/yt-project/yt_idv
.. _tarball: https://github.com/yt-project/yt_idv/tarball/master
