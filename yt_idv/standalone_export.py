"""
Export a yt data source as a scene that ``yt_idv.SceneGraph.load`` can open.

This file only depends on yt and numpy, so it can be copied to and run on a
machine where yt_idv (or OpenGL) is not available:

    python standalone_export.py DATASET FIELD OUTPUT [--no-ghost] [--float64]
        [--checkpoint-dir DIR]

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

With ``--checkpoint-dir`` each block is saved to that directory as soon as yt
has generated it, so an export that is killed (e.g., by a batch job's time
limit) can be resumed by running the same command again; only the blocks that
were not saved yet are generated. The directory is removed once the scene file
has been written.
"""

import argparse
import json
import os
import shutil
import zipfile

import numpy as np

FORMAT_VERSION = 1

_CAMERA_CLASS = "yt_idv.cameras.trackball_camera.TrackballCamera"
_DATA_CLASS = "yt_idv.scene_data.block_collection.BlockCollection"
_COMPONENT_CLASS = "yt_idv.scene_components.blocks.BlockRendering"
_TEXTURE_CLASS = "yt_idv.opengl_support.Texture3D"


def dataset_info(ds):
    """yt_idv.serialization.dataset_info, repeated so this module needs no OpenGL."""
    return {
        "unit_registry": ds.unit_registry.to_json(),
        "current_redshift": float(getattr(ds, "current_redshift", 0.0) or 0.0),
        "current_time": str(getattr(ds, "current_time", "")),
    }


class _Archive:
    # Arrays are written to the zip file as they are added, so they are not
    # all held in memory at once.
    def __init__(self, zf):
        self.zf = zf
        self.n_arrays = 0
        self.textures = []

    def add_array(self, arr):
        key = f"arrays/{self.n_arrays:06d}.npy"
        self.n_arrays += 1
        with self.zf.open(key, "w", force_zip64=True) as f:
            np.lib.format.write_array(f, np.asarray(arr), allow_pickle=False)
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

    def write_state(self, state):
        self.zf.writestr("scene.json", json.dumps(state, indent=2))


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


class _MemoryStore(dict):
    def save(self, i, record):
        self[i] = record

    def load(self, i, keys):
        return {k: self[i][k] for k in keys}


class _CheckpointStore:
    # Each block is written to a temporary file and then renamed, so a block
    # file is either complete or absent no matter when the export is killed.
    def __init__(self, path, manifest, tree):
        self.path = path
        manifest_fn = os.path.join(path, "manifest.json")
        tree_fn = os.path.join(path, "tree.npz")
        if os.path.exists(manifest_fn):
            with open(manifest_fn) as f:
                saved = json.load(f)
            with np.load(tree_fn) as f:
                same_tree = set(f.files) == set(tree) and all(
                    np.array_equal(f[k], v, equal_nan=True) for k, v in tree.items()
                )
            if saved != manifest or not same_tree:
                raise ValueError(
                    f"The checkpoint in {path} was made for a different export; "
                    "remove it to start over."
                )
            return
        os.makedirs(os.path.join(path, "blocks"), exist_ok=True)
        self._write(tree_fn, lambda f: np.savez(f, **tree))
        self._write(manifest_fn, lambda f: f.write(json.dumps(manifest).encode()))

    @staticmethod
    def _write(fn, write):
        with open(f"{fn}.tmp", "wb") as f:
            write(f)
        os.replace(f"{fn}.tmp", fn)

    def _block_fn(self, i):
        return os.path.join(self.path, "blocks", f"{i:06d}.npz")

    def __contains__(self, i):
        return os.path.exists(self._block_fn(i))

    def save(self, i, record):
        self._write(self._block_fn(i), lambda f: np.savez(f, **record))

    def load(self, i, keys):
        with np.load(self._block_fn(i), allow_pickle=False) as f:
            return {k: f[k] for k in keys}


def _generate_blocks(tiles, store, n_blocks):
    from yt.funcs import get_pbar

    pbar = get_pbar("Generating blocks", n_blocks)
    try:
        for i, node in enumerate(tiles.tree.trunk.kd_traverse()):
            if i not in store:
                brick = tiles.get_brick_data(node)
                data = brick.my_data[0]
                abs_data = np.abs(data)
                store.save(
                    i,
                    {
                        "data": np.asarray(data),
                        "mask": brick.source_mask,
                        "left_edge": brick.LeftEdge,
                        "right_edge": brick.RightEdge,
                        "dx": (brick.RightEdge - brick.LeftEdge)
                        / brick.source_mask.shape,
                        "min_val": np.asarray(np.nanmin(abs_data)),
                        "max_val": np.asarray(np.nanmax(abs_data)),
                        "units": np.array(str(getattr(data, "units", ""))),
                    },
                )
                node.data = None
            pbar.update(i + 1)
    finally:
        pbar.finish()


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
    checkpoint_dir=None,
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
    checkpoint_dir: A directory to save each block to as it is generated, so
                    that an interrupted export can be resumed by calling this
                    again with the same arguments; removed once the file has
                    been written
    """
    dtype = "f8" if float64 else "f4"
    ds = data_source.ds
    geometry = str(ds.geometry)
    if geometry != "cartesian":
        raise NotImplementedError(
            f"Only cartesian geometries can be exported, not {geometry}."
        )

    from yt.utilities.amr_kdtree.api import AMRKDTree

    # AMRKDTree.set_fields would generate every block in one call, which can
    # not be checkpointed, so the blocks are generated one at a time instead.
    # A tree of our own also keeps the data source's cached tree untouched.
    tiles = AMRKDTree(ds, data_source=data_source)
    tiles.fields = data_source._determine_fields([field])
    tiles.log_fields = [False]
    tiles.no_ghost = no_ghost
    field = tiles.fields[0]

    tree = _flatten_kd_tree(tiles.tree.trunk)
    bbox = np.array([edge.to("unitary").d for edge in data_source.get_bbox()])
    if checkpoint_dir is None:
        store = _MemoryStore()
    else:
        manifest = {
            "dataset": str(ds),
            "unique_identifier": str(getattr(ds, "unique_identifier", "")),
            "field": list(field),
            "no_ghost": bool(no_ghost),
            "bbox": bbox.tolist(),
        }
        store = _CheckpointStore(checkpoint_dir, manifest, tree)
    n_blocks = int((tree["block"] >= 0).sum())
    _generate_blocks(tiles, store, n_blocks)

    keys = ("left_edge", "right_edge", "dx", "min_val", "max_val")
    summary = [store.load(i, keys) for i in range(n_blocks)]
    field_units = str(store.load(0, ("units",))["units"])
    min_val = float(min(b["min_val"] for b in summary))
    max_val = float(max(b["max_val"] for b in summary))

    dx = np.array([b["dx"] for b in summary])
    le = np.array([b["left_edge"] for b in summary])
    re = np.array([b["right_edge"] for b in summary])
    diagonal = float(np.sqrt(((re.max(axis=0) - le.min(axis=0)) ** 2).sum()))
    ratio = (ds.units.code_length / ds.units.unitary).base_value

    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    partial = f"{filename}.partial"
    try:
        with zipfile.ZipFile(partial, "w", compression=mode, allowZip64=True) as zf:
            archive = _Archive(zf)
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
                        ("model_vertex", np.ones((n_blocks, 4), dtype="f4")),
                        ("in_dx", (dx * ratio).astype(dtype)),
                        ("in_left_edge", (le * ratio).astype(dtype)),
                        ("in_right_edge", (re * ratio).astype(dtype)),
                    )
                ],
            }

            block_data = []
            block_bitmaps = []
            for i in range(n_blocks):
                block = store.load(i, ("data", "mask"))
                n_data = np.abs(block["data"]).astype(dtype)
                if max_val != min_val:
                    n_data = (n_data - min_val) / (max_val - min_val)
                    n_data[n_data < 0] = 0.0
                    n_data[n_data > 1] = 1.0
                    # zero-valued blocks are skipped by the shader
                    n_data[n_data == 0.0] += np.finfo(np.float32).eps
                block_data.append([i, archive.add_array(n_data)])
                block_bitmaps.append(
                    [i, archive.add_array((block["mask"] * 255).astype("uint8"))]
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
                    "_kd_tree": {k: archive.add_array(v) for k, v in tree.items()},
                    "diagonal": diagonal,
                    # the data source's bounding box (unitary), BlockCollection.bbox
                    "_bbox": archive.add_array(bbox),
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
                "traits": {}
                if render_method is None
                else {"render_method": render_method},
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
                "dataset": dataset_info(ds),
            }
            archive.write_state(state)
    except BaseException:
        if os.path.exists(partial):
            os.remove(partial)
        raise
    os.replace(partial, filename)
    if checkpoint_dir is not None:
        shutil.rmtree(checkpoint_dir)


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
    parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="save blocks here as they are generated, so that running the same "
        "command again resumes an interrupted export",
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
        checkpoint_dir=args.checkpoint_dir,
    )


if __name__ == "__main__":
    main()
