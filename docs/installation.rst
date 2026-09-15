.. highlight:: shell

============
Installation
============


Stable release
--------------

yt_idv includes an optional interactive GUI but at present the GUI is limited to  python 3.12 and lower.
For 3.13+ you can install without the GUI and run in headless mode.

To install yt_idv without GUI support, run this command in your terminal:

.. code-block:: console

    $ python -m pip install yt_idv

To install yt_idv with the GUI, run this command in your terminal:

.. code-block:: console

    $ python -m pip install "yt_idv[gui]"

This is the preferred method to install yt_idv, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _gui-extra:

Interactive GUI (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~

The interactive control panel drawn over the ``pyglet`` window is built on
`imgui <https://pypi.org/project/imgui/>`_, which is an optional dependency.
To use the GUI, install ``yt_idv`` with the ``gui`` extra:

.. code-block:: console

    $ python -m pip install "yt_idv[gui]"

Without the extra, ``yt_idv`` can still render offscreen with the ``osmesa``
or ``egl`` contexts, or in a hidden ``pyglet`` window with
``render_context("pyglet", visible=False, gui=False)`` (see :doc:`usage`).
Requesting a GUI without ``imgui`` installed raises an ``ImportError``.

.. note::

   ``imgui`` does not currently build on python 3.13 or newer, so on those
   versions only the headless install is available.

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

    $ python -m pip install .


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
pyglet (see :doc:`usage`). If it returns ``Background`` or ``StandardIO`` then
no window session is available (expected over ``ssh``) and you'll need to
install extra libraries for headless rendering.

Headless rendering on macOS without window server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``OSMesa`` has been deprecated on Mesa builds for macOS, so it is
recommended that you use ``egl`` installed through Mesa. The following
should provide ``libEGL`` and ``libGL``:

.. code-block:: console

    $ brew install mesa

Then request the ``egl`` engine as usual::

    rc = yt_idv.render_context("egl", width=1024, height=1024)

``yt_idv`` handles the macOS-specific wrinkles for you when it builds an EGL
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
