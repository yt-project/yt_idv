import numpy as np
import traitlets
from yt.data_objects.data_containers import YTDataContainer
from yt.utilities.lib.mesh_triangulation import triangulate_mesh
from yt_idv.opengl_support import Texture3D, VertexArray, VertexAttribute
from yt_idv.scene_data.base_data import SceneData


class MeshData(SceneData):
    name = "mesh"
    data_source = traitlets.Instance(YTDataContainer)
    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    texture_objects = traitlets.Dict(trait=traitlets.Instance(Texture3D))
    blocks = traitlets.Dict(default_value=())
    scale = traitlets.Bool(False)
    size = traitlets.CInt(-1)

    def get_mesh_data(self, data_source, field):
        """

        This reads the mesh data into a form that can be fed in to OpenGL.

        """

        # get mesh information
        try:
            ftype, fname = field
            mesh_id = int(ftype[-1])
        except ValueError:
            mesh_id = 0

        mesh = data_source.ds.index.meshes[mesh_id - 1]
        offset = mesh._index_offset
        vertices = mesh.connectivity_coords
        indices = mesh.connectivity_indices - offset

        data = data_source[field]

        return triangulate_mesh(vertices, data, indices)

    def add_data(self, field):
        v, d, i = self.get_mesh_data(self.data_source, field)
        v.shape = (v.size // 3, 3)
        v = np.concatenate([v, np.ones((v.shape[0], 1))], axis=-1).astype("f4")
        d.shape = (d.size, 1)
        i.shape = (i.size, 1)
        i = i.astype("uint32")
        # d[:] = np.mgrid[0.0:1.0:1j*d.size].astype("f4")[:,None]
        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=v)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="vertex_data", data=d.astype("f4"))
        )
        self.vertex_array.indices = i
        self.size = i.size

    @traitlets.default("vertex_array")
    def _default_vertex_array(self):
        return VertexArray(name="mesh_info", each=0)


class SliceData(MeshData):
    # a class to construct a mesh source from an axis-normal slice.
    name = "slice"
    _frb_args = None
    _mesh_ds = None

    def add_data(self, field, width=1., resolution=(400, 400), center=None, height=None, periodic=False):
        """
        adds the slice data for a field. This will generate a fixed resolution buffer
        of the slice and then construct an unstructured mesh representing the plane.
        Use the keyword arguments to control the FixedResolutionBuffer.


        Parameters
        ----------
        field : tuple
            ("field_type", "fieldname") tuple

        The remaining keyword arguments (width, resolution, center, height, periodic)
        are all passed to YTSlice.to_frb().


        """

        # store our frb arguments for now. get_mesh_data will extract the frb.
        self._frb_args = (width, resolution, center, height, periodic)
        super().add_data(field)

    def get_mesh_data(self, data_source, field):
        # must return output from triangulate_mesh(vertices, data, indices)
        frb = data_source.to_frb(*self._frb_args)
        coords, conn, e_data = self._mesh_from_frb(frb, field)
        return triangulate_mesh(coords, e_data, conn)

    def _assemble(self, xe, ye, ze, nx, ny, nz, frb_array):
        # assemble elements! this is a first pass brute force approach...

        # containers that can be given to yt.load_unstructured()
        coords = []
        connectivity = []
        element_center_data = []
        icoord = 0

        def sample_the_frb(ix, iy, iz):
            # the index order depends on which axis is orthogonal to our slice!
            if nx == 1:
                data = frb_array[iy, iz]
            elif ny == 1:
                data = frb_array[ix, iz]
            elif nz == 1:
                data = frb_array[ix, iy]
            else:
                raise ValueError("One of the mesh dimensions must have a single element!")
            return data

        # this could be vectorized. but it's not as bad as it could be since
        # one of the dimensions will always have 1 element. but it is still slow
        # and needs to be improved...
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):

                    # add vertices of our hexahedral elements (in the proper order!)
                    # to our coordinate array (this will repeat vertices in the
                    # coordinate array)
                    verts = [
                        [xe[ix], ye[iy], ze[iz]],
                        [xe[ix + 1], ye[iy], ze[iz]],
                        [xe[ix + 1], ye[iy + 1], ze[iz]],
                        [xe[ix], ye[iy + 1], ze[iz]],
                        [xe[ix], ye[iy], ze[iz + 1]],
                        [xe[ix + 1], ye[iy], ze[iz + 1]],
                        [xe[ix + 1], ye[iy + 1], ze[iz + 1]],
                        [xe[ix], ye[iy + 1], ze[iz + 1]]
                    ]
                    coords += verts

                    # because we are repeating our vertices, connectivity can
                    # just be incremented
                    connectivity += [[i for i in range(icoord, icoord + 8)], ]
                    icoord += 8

                    these_vals = sample_the_frb(ix, iy, iz)
                    element_center_data.append(these_vals)

        # finalize our arrays
        coords = np.array(coords)
        connectivity = np.array(connectivity)
        element_center_data = np.array(element_center_data)

        return coords, connectivity, element_center_data

    def _mesh_from_frb(self, frb, field):
        """Construct an unstructured mesh of a slice's frb for the given field.

        This function builds a hexahedral mesh with the frb values as
        element-center values. Mesh vertices are given by a uniform grid surrounding
        the center of each frb point that is a single element wide in the direction
        normal to the plane. The thickness of the slice is set as a fraction of the
        minimum cell width in the slice-axes.

        Parameters
        ----------
        frb : FixedResolutionBuffer
            generated from YTSlice.to_frb()
        field : tuple
            ("fieldtype", "fieldname")

        Returns
        -------
        tuple
            coords : ndarray, vertex coordinates with shape (Nverts, 3)
            conn : ndarray, connectivity indices with shape (Ncells, 8)
            e_center_data : ndarray, element-center data with shape (Ncells, )
        """

        # extract frb values and extract slice info
        frb_vals = frb[field]
        parent_slice = frb.data_source  # YTSlice object
        coord = parent_slice.coord  # the position along the axis we're slicing at
        bounds = frb.bounds  # (x min, x max, y min, y max) of the image axes
        axis = parent_slice.axis  # the slice normal axis

        # build a 3d mesh. frb values will be cell-centered values, will build
        # a grid to to surround the cell-centered values.

        # first decide on the thickness of our cells in the slice-orthoganal direction
        d1 = (bounds[1] - bounds[0]) / frb.buff_size[0]
        d2 = (bounds[2] - bounds[3]) / frb.buff_size[1]
        slice_width_factor = 0.01  # could be an input
        pseudo_d = np.min([d1, d2]) * slice_width_factor  # our slice width!
        pseudo_bounds = [coord - pseudo_d / 2., coord + pseudo_d / 2.]

        # now set the bounds and number of cells in each direction. The axis
        # orthogonal to slicing plane will always have 1 element.
        if axis == 0:
            nx = 1
            xlims = pseudo_bounds
            ny = frb.buff_size[0]
            ylims = [bounds[0], bounds[1]]
            nz = frb.buff_size[1]
            zlims = [bounds[2], bounds[3]]
        elif axis == 1:
            nx = frb.buff_size[0]
            xlims = [bounds[0], bounds[1]]
            ny = 1
            ylims = pseudo_bounds
            nz = frb.buff_size[1]
            zlims = [bounds[2], bounds[3]]
        elif axis == 2:
            nx = frb.buff_size[0]
            xlims = [bounds[0], bounds[1]]
            ny = frb.buff_size[1]
            ylims = [bounds[2], bounds[3]]
            nz = 1
            zlims = pseudo_bounds

        # construct cell-center arrays, cell widths and cell vertices arrays for
        # each axis
        def get_grid_axis(lims, N):
            grid_spacing = (lims[1] - lims[0]) / N
            hlf = grid_spacing / 2.
            grid_edges = np.linspace(lims[0] - hlf, lims[1] + hlf, N+1)
            return grid_edges, grid_spacing

        xe, dx = get_grid_axis(xlims, nx)
        ye, dy = get_grid_axis(ylims, ny)
        ze, dz = get_grid_axis(zlims, nz)

        # get our unstructured mesh (slow right now)
        coords, conn, e_center_data = self._assemble(xe, ye, ze, nx, ny, nz, frb_vals)
        return coords, conn, e_center_data


class SliceComposite(MeshData):
    name = "slice_composite"

    def add_data(self, slices):
        """combines SliceData objects into a single SliceComposite.

        Parameters
        ----------
        slices : list or tuple
            a list/tuple of SliceData objects that already have data added.
        """
        if type(slices) not in (tuple, list):
            slices = [slices]

        verts = []
        edata = []
        indices = []
        index_max = 0
        for slc in slices:
            if isinstance(slc, SliceData) is False:
                raise TypeError("all slices must be a SliceData objects")

            for attr in slc.vertex_array.attributes:
                if attr.name == "model_vertex":
                    verts.append(attr.data)
                elif attr.name == "vertex_data":
                    edata.append(attr.data)
            indices.append( slc.vertex_array.indices + index_max)
            index_max += slc.size

        verts = np.concatenate(verts)
        edata = np.concatenate(edata)
        indices = np.concatenate(indices)

        self.vertex_array.attributes.append(
            VertexAttribute(name="model_vertex", data=verts)
        )
        self.vertex_array.attributes.append(
            VertexAttribute(name="vertex_data", data=edata.astype("f4"))
        )
        self.vertex_array.indices = indices
        self.size = indices.size
