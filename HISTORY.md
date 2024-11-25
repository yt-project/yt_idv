# History

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
