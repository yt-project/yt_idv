"""
Export a yt data source as a scene that ``yt_idv.SceneGraph.load`` can open.

This file only depends on yt and numpy, so it can be copied to and run on a
machine where yt_idv (or OpenGL) is not available:

    python standalone_export.py DATASET FIELD OUTPUT [--no-ghost] [--float64]

or, from python:

    from standalone_export import export_block_scene
    export_block_scene(ds.all_data(), "density", "scene.zip")

Then, wherever yt_idv is available:

    rc = yt_idv.render_context(height=800, width=800)
    rc.scene = yt_idv.scene_graph.SceneGraph.load("scene.zip")
    rc.run()

Only cartesian geometries are supported. The block processing mirrors
``BlockCollection.add_data`` and the file layout mirrors
``yt_idv.serialization``.

With ``--float64`` the vertex geometry and texture data are stored in float64;
yt_idv casts them down to float32 only for the GPU. That keeps deep zooms into
highly refined data exact, at the cost of a larger file (the textures double in
size), and needs a yt_idv that can load float64 scenes.
"""

import argparse
import json
import zipfile

import numpy as np

FORMAT_VERSION = 1

_CAMERA_CLASS = "yt_idv.cameras.trackball_camera.TrackballCamera"
_DATA_CLASS = "yt_idv.scene_data.block_collection.BlockCollection"
_COMPONENT_CLASS = "yt_idv.scene_components.blocks.BlockRendering"
_TEXTURE_CLASS = "yt_idv.opengl_support.Texture3D"


class _Archive:
    def __init__(self):
        self.arrays = {}
        self.textures = []

    def add_array(self, arr):
        key = f"arrays/{len(self.arrays):06d}.npy"
        self.arrays[key] = np.asarray(arr)
        return {"__array__": key}

    def add_texture(self, data, **parameters):
        self.textures.append(
            {
                "class": _TEXTURE_CLASS,
                "parameters": parameters,
                "data": self.add_array(data),
            }
        )
        return {"__texture__": len(self.textures) - 1}

    def write(self, filename, state, compress=False):
        mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        with zipfile.ZipFile(filename, "w", compression=mode, allowZip64=True) as zf:
            zf.writestr("scene.json", json.dumps(state, indent=2))
            for key, arr in self.arrays.items():
                with zf.open(key, "w", force_zip64=True) as f:
                    np.lib.format.write_array(f, arr, allow_pickle=False)


def _flatten_kd_tree(trunk):
    nodes = list(trunk.depth_traverse())
    index = {id(node): i for i, node in enumerate(nodes)}
    n = len(nodes)
    left = np.full(n, -1, dtype="int64")
    right = np.full(n, -1, dtype="int64")
    split_dim = np.full(n, -1, dtype="int64")
    split_pos = np.full(n, np.nan, dtype="float64")
    block = np.full(n, -1, dtype="int64")
    n_blocks = 0
    for i, node in enumerate(nodes):
        if node.kd_is_leaf():
            if node.grid != -1:
                block[i] = n_blocks
                n_blocks += 1
            continue
        left[i] = index[id(node.left)]
        right[i] = index[id(node.right)]
        split_dim[i] = node.get_split_dim()
        split_pos[i] = node.get_split_pos()
    return {
        "left": left,
        "right": right,
        "split_dim": split_dim,
        "split_pos": split_pos,
        "block": block,
    }


def _camera_state(ds):
    center = ds.domain_center.to("unitary").d
    position = center + 1.5 * ds.domain_width.to("unitary").d
    near_plane = 3.0 * ds.index.get_smallest_dx().min().to("unitary").d
    return {
        "position": position.tolist(),
        "focus": center.tolist(),
        "up": [0.0, 1.0, 0.0],
        "near_plane": max(float(near_plane), 1e-5),
    }


def export_block_scene(
    data_source,
    field,
    filename,
    no_ghost=False,
    render_method=None,
    compress=False,
    float64=False,
):
    """
    Write a volume rendering of a data source to a yt_idv scene file.

    Parameters
    ----------
    data_source: yt data container such as a sphere, region, etc
    field: The field to volume render
    filename: The file to write
    no_ghost: Should we save time by skipping ghost zone generation
    render_method: The BlockRendering render method (e.g., "projection");
                   uses the yt_idv default if None
    compress: Should the file be compressed (slower, but often smaller)
    float64: Store the vertex geometry and texture data in float64 (yt_idv
             casts them to float32 for the GPU); otherwise float32
    """
    dtype = "f8" if float64 else "f4"
    ds = data_source.ds
    geometry = str(ds.geometry)
    if geometry != "cartesian":
        raise NotImplementedError(
            f"Only cartesian geometries can be exported, not {geometry}."
        )

    tiles = data_source.tiles
    tiles.set_fields([field], [False], no_ghost=no_ghost)
    field = data_source._determine_fields(field)[0]

    blocks = list(tiles.traverse())
    field_units = str(getattr(blocks[0].my_data[0], "units", ""))
    min_val = min(np.nanmin(np.abs(b.my_data[0])) for b in blocks)
    max_val = max(np.nanmax(np.abs(b.my_data[0])) for b in blocks)
    min_val = float(getattr(min_val, "d", min_val))
    max_val = float(getattr(max_val, "d", max_val))

    dx = np.array([(b.RightEdge - b.LeftEdge) / b.source_mask.shape for b in blocks])
    le = np.array([b.LeftEdge for b in blocks])
    re = np.array([b.RightEdge for b in blocks])
    diagonal = float(np.sqrt(((re.max(axis=0) - le.min(axis=0)) ** 2).sum()))
    ratio = (ds.units.code_length / ds.units.unitary).base_value

    archive = _Archive()
    vertex_array = {
        "name": "block_info",
        "each": 1,
        "indices": None,
        "attributes": [
            {
                "name": name,
                "divisor": 0,
                "data": archive.add_array(arr),
            }
            for name, arr in (
                ("model_vertex", np.ones((len(blocks), 4), dtype="f4")),
                ("in_dx", (dx * ratio).astype(dtype)),
                ("in_left_edge", (le * ratio).astype(dtype)),
                ("in_right_edge", (re * ratio).astype(dtype)),
            )
        ],
    }

    block_data = []
    block_bitmaps = []
    for i, block in enumerate(blocks):
        n_data = np.abs(block.my_data[0]).copy(order="F").astype(dtype).d
        if max_val != min_val:
            n_data = (n_data - min_val) / (max_val - min_val)
            n_data[n_data < 0] = 0.0
            n_data[n_data > 1] = 1.0
            # zero-valued blocks are skipped by the shader
            n_data[n_data == 0.0] += np.finfo(np.float32).eps
        block_data.append([i, archive.add_array(n_data)])
        block_bitmaps.append(
            [i, archive.add_array((block.source_mask * 255).astype("uint8"))]
        )

    block_collection = {
        "class": _DATA_CLASS,
        "traits": {
            "min_val": min_val,
            "max_val": max_val,
            "field": list(field),
            "field_units": field_units,
            "_yt_geom_str": geometry,
        },
        "attributes": {
            "vertex_array": {"__vertex_array__": vertex_array},
            "textures": [],
            "block_data": {"__items__": block_data},
            "block_bitmaps": {"__items__": block_bitmaps},
            "_kd_tree": {
                k: archive.add_array(v)
                for k, v in _flatten_kd_tree(tiles.tree.trunk).items()
            },
            "diagonal": diagonal,
            # the data source's bounding box (unitary), BlockCollection.bbox
            "_bbox": archive.add_array(
                np.array([edge.to("unitary").d for edge in data_source.get_bbox()])
            ),
            # float64 unscaled edges (unitary) and the unit conversion, so the
            # scene can be scaled and rescaled without losing precision
            "_unscaled_edges": archive.add_array(
                np.array([le * ratio, re * ratio, dx * ratio])
            ),
            "_unitary_per_code_length": ratio,
        },
    }
    component = {
        "class": _COMPONENT_CLASS,
        "traits": {} if render_method is None else {"render_method": render_method},
        "attributes": {},
        "data": {"__data__": 0},
    }
    state = {
        "format_version": FORMAT_VERSION,
        "camera": {"class": _CAMERA_CLASS, "state": _camera_state(ds)},
        "n_scene_data_objects": 1,
        "components": [component],
        "annotations": [],
        "data_objects": [block_collection],
        "textures": archive.textures,
    }
    archive.write(filename, state, compress=compress)


def main():
    import yt

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dataset", help="the dataset to load with yt.load")
    parser.add_argument(
        "field", help="the field to render, e.g. density or gas,density"
    )
    parser.add_argument("output", help="the scene file to write")
    parser.add_argument("--no-ghost", action="store_true", help="skip ghost zones")
    parser.add_argument("--render-method", default=None, help="e.g. projection")
    parser.add_argument("--compress", action="store_true", help="compress the file")
    parser.add_argument(
        "--float64",
        action="store_true",
        help="store the geometry and texture data in float64 (larger file)",
    )
    args = parser.parse_args()

    ds = yt.load(args.dataset)
    field = tuple(args.field.split(",")) if "," in args.field else args.field
    export_block_scene(
        ds.all_data(),
        field,
        args.output,
        no_ghost=args.no_ghost,
        render_method=args.render_method,
        compress=args.compress,
        float64=args.float64,
    )


if __name__ == "__main__":
    main()
