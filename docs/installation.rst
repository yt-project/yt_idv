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

If you're using a machine with a logged-in window server session, you can use a
hidden pyglet window for headless rendering with the GPU. If you're not sure,
run the following from a terminal:

.. code-block:: console

    $ launchctl managername
    Aqua

If ``Aqua`` is returned, a window server session is active and you can use
pyget (see ). If it returns ``Background`` or ``StandardIO`` then no window
session is available (expected over ``ssh``) and you'll need to install
extra libraries for headless rendering.

Headless rendering on macOS without window server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``OSMesa`` been deprecated on Mesa builds for macOS, so it is
recommended that you use ``egl`` installed through Mesa. The following
should provide ``libEGL`` and ``libGL``:

.. code-block:: console

    $ brew install mesa

Then request the ``egl`` engine as usual::

    rc = yt_idv.render_context("egl", width=1024, height=1024)

``yt_idv`` handles the two macOS-specific wrinkles for you when it builds an EGL
context on darwin. Mesa is searched for under ``$YT_IDV_MESA_PREFIX``, ``$CONDA_PREFIX``,
``/opt/homebrew``, ``/usr/local`` and ``/opt/local`` (in that order, checking
both ``lib/`` and ``opt/mesa/lib/``).  If yours lives somewhere else, point
``yt_idv`` at it:

.. code-block:: console

    $ export YT_IDV_MESA_PREFIX=/path/to/mesa   # contains lib/libEGL.dylib


While ``OSMesa`` is not recommended for new installs, the ``yt_idv`` test suite
only runs on ``OSMesa`` at present. So to run on macOS, you'd
need to install an older version of Mesa (25.0.5 or below). You can do so from conda
easily with ``conda install mesalib<=25.0.5``.


.. _Github repo: https://github.com/yt-project/yt_idv
.. _tarball: https://github.com/yt-project/yt_idv/tarball/master
