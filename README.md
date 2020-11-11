# interactive volume rendering for yt

[![](https://img.shields.io/pypi/v/yt_idv.svg)](https://pypi.python.org/pypi/yt_idv)

[![Doc Status](https://readthedocs.org/projects/yt-idv/badge/?version=latest)](https://yt-idv.readthedocs.io/en/latest/?badge=latest)

This package provides interactive visualization using OpenGL for datasets
loaded in yt.  It is written to provide both scripting and interactive access.

* Free software: BSD license
* Documentation: https://yt-idv.readthedocs.io.

![example of using yt_idv](https://i.imgur.com/Q4XPNZw.gif)

## Features

* Rendering of multi-resolution (AMR) volume data
* Rendering of unstructured mesh data
* Fully-traitlets-ized interface for controlling the rendering properties
* DearImGUI-based interactive controls
* On-screen rendering powered by [pyglet](http://pyglet.org/) and off-screen
  [EGL](https://en.wikipedia.org/wiki/EGL_(API)) through [PyOpenGL](https://pypi.org/project/PyOpenGL/)
* Multiple annotations:
    * Text
    * Boxes
    * Block and grid outlines
* Support for sub-selections of data via the yt data selection interface
* Integration with the [ipywidgets](https://ipywidgets.readthedocs.org/) ``Image`` widget.

## Examples

## Credits

This package was initially created as part of [yt](https://yt-project.org), with the first iteration written by
Chuck Rozhon.  The conversion to use traitlets, pyglet and a more flexible shader interface was done by Matthew Turk,
with contributions from Kacper Kowalik and Chris Havlin.

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[`audreyr/cookiecutter-pypackage`](https://github.com/audreyr/cookiecutter-pypackage) project template.
