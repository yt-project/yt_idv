# History

## 0.5.0

## Highlights

**Spherical Coordinates!** With this release, yt_idv can now volume render yt datasets defined in spherical coordinates. To use it, just try to load a 3D spherical dataset (gridded AMR and uniform grids only at present) and let us know if it breaks! For an overview of how it works, see the docs [here](https://yt-idv.readthedocs.io/en/latest/coordinate_systems.html) or try out the new example scripts: [spherical_unigrid_rendering.py](https://github.com/yt-project/yt_idv/blob/main/examples/spherical_unigrid_rendering.py) and [spherical_amr_rendering_with_refinement](https://github.com/yt-project/yt_idv/blob/main/examples/spherical_amr_rendering_with_refinement.py). Changes in [159](https://github.com/yt-project/yt_idv/pull/159), stay tuned for a paper...

**More colormaps!** In [154](https://github.com/yt-project/yt_idv/pull/154) and [155](https://github.com/yt-project/yt_idv/pull/155), many more colormaps were added to the colormap dropdown, including all of the colormaps from [cmyt](https://github.com/yt-project/cmyt/).

### Changes

#### New Features
* Volume Rendering datasets in spherical coordinates by @chrishavlin in https://github.com/yt-project/yt_idv/pull/159
* Add more colormaps and _r colormaps by @matthewturk in https://github.com/yt-project/yt_idv/pull/154
* Add cmyt cmaps too!  by @chrishavlin in https://github.com/yt-project/yt_idv/pull/155
* Multiple views in a single window by @matthewturk in https://github.com/yt-project/yt_idv/pull/137
* Add some camera adjustments by @matthewturk in https://github.com/yt-project/yt_idv/pull/156
* add `TrackballCamera.from_dataset(ds)`, add example of manual `SceneGraph` contstruction by @chrishavlin in https://github.com/yt-project/yt_idv/pull/190

#### Infrastructure Improvements and Bug Fixes
* Add tests for shader program compilation by @chrishavlin in https://github.com/yt-project/yt_idv/pull/133
* link to examples directory in readme by @chrishavlin in https://github.com/yt-project/yt_idv/pull/134
* set PYOPENGL_PLATFORM before opengl imports by @chrishavlin in https://github.com/yt-project/yt_idv/pull/149
* update release actions, contributing notes by @chrishavlin in https://github.com/yt-project/yt_idv/pull/151
* Add text to avoid crash with imgui 2 by @matthewturk in https://github.com/yt-project/yt_idv/pull/153
* add a note on why ratio is needed in BlockCollection.add_data by @chrishavlin in https://github.com/yt-project/yt_idv/pull/158
* fix extras deprecation warning by @chrishavlin in https://github.com/yt-project/yt_idv/pull/162
* preprocessor directives followup  by @chrishavlin in https://github.com/yt-project/yt_idv/pull/89
* add camera.set_position to TrackballCamera by @chrishavlin in https://github.com/yt-project/yt_idv/pull/166
* offset the normalized block data by eps by @chrishavlin in https://github.com/yt-project/yt_idv/pull/172
* update constant_rgba blend func, rm linewidth from curve render by @chrishavlin in https://github.com/yt-project/yt_idv/pull/175
* Displaying camera dictionary, updating from dict by @chrishavlin in https://github.com/yt-project/yt_idv/pull/180
* Use only intersected grids for GridOutline by @chrishavlin in https://github.com/yt-project/yt_idv/pull/179
* use gi in slice_traverse loop not i by @chrishavlin in https://github.com/yt-project/yt_idv/pull/182
* BUG: remove scaling from block outlines for spherical datasets by @chrishavlin in https://github.com/yt-project/yt_idv/pull/188
* Setting fixed data normalization and color map limits by @chrishavlin in https://github.com/yt-project/yt_idv/pull/191
* add py 3.12 to CI, setup by @chrishavlin in https://github.com/yt-project/yt_idv/pull/192


**Full Changelog**: https://github.com/yt-project/yt_idv/compare/v0.4.1...v0.5.0

## 0.4.1

Bug fix release to fix slicing issue, some test improvements.

### Changes
* add test for curves, fix traitlets deprecation warnings, update github action versions by @chrishavlin in https://github.com/yt-project/yt_idv/pull/128
* BUG: Fix slice rendering by @chrishavlin in https://github.com/yt-project/yt_idv/pull/131

**Full Changelog**: https://github.com/yt-project/yt_idv/compare/v0.4.0...v0.4.1

## 0.4.0
This release provides full support for numpy 2 and a number of other changes related to deprecations and maintenance.

### Changes

* update readthedocs config by @chrishavlin in https://github.com/yt-project/yt_idv/pull/99
* Update dependency organization, build-test action by @chrishavlin in https://github.com/yt-project/yt_idv/pull/98
* add 3.10,3.11 to CI, drop 3.8 test by @chrishavlin in https://github.com/yt-project/yt_idv/pull/97
* fix some warnings by @chrishavlin in https://github.com/yt-project/yt_idv/pull/100
* Don't use deprecated matplotlib.cm.get_cmap. by @anntzer in https://github.com/yt-project/yt_idv/pull/118
* Updates for np 2 and more by @chrishavlin in https://github.com/yt-project/yt_idv/pull/123
* Fix docs build by @chrishavlin in https://github.com/yt-project/yt_idv/pull/124

### New Contributors
* @anntzer made their first contribution in https://github.com/yt-project/yt_idv/pull/118

**Full Changelog**: https://github.com/yt-project/yt_idv/compare/v0.3.1...v0.4.0

## 0.3.1

* add a display_name attribute by @chrishavlin in [62](https://github.com/yt-project/yt_idv/pull/62)
* preprocessor directives by @matthewturk in [70](https://github.com/yt-project/yt_idv/pull/70)
* Set unitary scale for the block collection by @matthewturk in [79](https://github.com/yt-project/yt_idv/pull/79)
* ds_tex objects by @matthewturk in [47](https://github.com/yt-project/yt_idv/pull/47)
* isocontour improvements by @chrishavlin in [43](https://github.com/yt-project/yt_idv/pull/43)
* installation note for wayland on linux by @chrishavlin in [82](https://github.com/yt-project/yt_idv/pull/82)
* updates to documentation by @chrishavlin in [85](https://github.com/yt-project/yt_idv/pull/85)

**Full Changelog**: https://github.com/yt-project/yt_idv/compare/v0.3.0...v0.3.1

## 0.3.0

* minimum yt version is now 4.1
* Added isocontour shader by @sochowski in [40](https://github.com/yt-project/yt_idv/pull/40)
* Block-rendering based slicing by @matthewturk in [13](https://github.com/yt-project/yt_idv/pull/13)
* Curve plotting by @chrishavlin in [26](https://github.com/yt-project/yt_idv/pull/26)
* Pop-up help by @chrishavlin in [44](https://github.com/yt-project/yt_idv/pull/44)
* allow uniform arrays by @matthewturk in [38](https://github.com/yt-project/yt_idv/pull/38)
* Make windows resizable by @matthewturk in [57](https://github.com/yt-project/yt_idv/pull/57)

**Full Changelog**: [v0.2.3-v0.3.0](https://github.com/yt-project/yt_idv/compare/v0.2.3...v0.3.0)

## 0.2.3
* Fixes to manifest, restoring pypi functionality.

## 0.2.2
* bug fixes and improvements: full change history to come in upcoming minor release.

## 0.2.0

* Add grid positions annotation
* Add OSMesa rendering context for off-screen rendering
* Add geometry shader support
* Add tests and a handful of new examples
* Fix rendering meshes
* Regularize uniform names across shaders

## 0.1.0

* First release on PyPI.
