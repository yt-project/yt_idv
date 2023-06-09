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

.. _Github repo: https://github.com/yt-project/yt_idv
.. _tarball: https://github.com/yt-project/yt_idv/tarball/master
