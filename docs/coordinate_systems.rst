.. highlight:: shell

================================
Non-Cartesian Coordinate Systems
================================

Initial support for volume rendering of data defined in 3D non-cartesian coordinate systems
was added in yt_idv 0.5.0 for block-AMR data in spherical coordinates. While not all
rendering methods and annotations are supported for spherical coordinates, yt_idv can
directly calculate maximum intensity projections, integrative projections and projection with custom
transfer functions without any pre-interpolation or re-gridding (with some caveats).

PUT A NICE SCREEN SHOT HERE.

---------------------------------------------------
Volume Rendering of Data in a Spherical Coordinates
---------------------------------------------------

Overview

#. pre-calculation of cartesian bounding boxes of the amr blocks, accelerated with cython.
#. load block data as textures in normalized native coordinates (just like cartesian)
#. pass down cartesian boudning boxes and spherical bounding boxes of blocks as vertex attributes
#. standard slab test with the cartesian bounding boxes for ray-element intersections
#. step along ray, calculate spherical coordinates (in the shader!), evalulate texture (discarding points outside the actual speherical volume element).


Mention: Pre-processor switches in order to re-use carteisan shaders efficiently.

The main limitation in this approach is in stepping along the ray: intersection with the
 cartesian bounding box of a spherical element does not gaurentee intersection with the enclosed
spherical elemnt. So a fairly large number of sample points along the ray must be used, increasing
the computational cost to achieve the same fidelity as rendering data that is natively in
cartesian coordinates.

----------------------------
Notes on further development
----------------------------

Further contributions are welcome for adding support for the remaining 3d non-cartesian coordinate systems
that yt supports that are not yet supported here (3d cylindrical, 3d geographic) as well as for adding
support for non-cartesian coordinate systems in additional yt_idv components.

****************************************
Supporting additional coordinate systems
****************************************

Describe coordinate_utilities.pyx (and .pxd), how to add a new coordinate system.

***************************************
Supporting additional rendering methods
***************************************

Adding additional coordiante system conversions to shaders (with pre-processor
directives).
