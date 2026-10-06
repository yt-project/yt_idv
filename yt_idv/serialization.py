"""
Saving and loading the state of a SceneGraph.

A saved scene is a zip archive holding ``scene.json``, which records each
object's class and its traits tagged with ``config=True``, and ``.npy`` files
for the textures and vertex data referenced from it.
"""

import importlib
import json
import zipfile

import numpy as np
import traitlets

from yt_idv.opengl_support import ColormapTexture, Texture, VertexArray, VertexAttribute

FORMAT_VERSION = 1
_SCENE_FILE = "scene.json"
_ARRAY_DIR = "arrays"

_TEXTURE_PARAMETERS = (
    "min_filter",
    "mag_filter",
    "boundary_x",
    "boundary_y",
    "boundary_z",
)


def _class_path(obj):
    cls = type(obj)
    return f"{cls.__module__}.{cls.__qualname__}"


def _import_class(path):
    module_name, _, class_name = path.rpartition(".")
    return getattr(importlib.import_module(module_name), class_name)


class SceneWriter:
    """Encodes scene objects into JSON-compatible values, collecting arrays."""

    def __init__(self):
        self.arrays = {}
        self.textures = []
        self.data_objects = []
        self._array_keys = {}
        self._texture_ids = {}
        self._data_ids = {}

    def add_array(self, arr):
        arr = np.asarray(arr)
        key = self._array_keys.get(id(arr))
        if key is None:
            key = f"{_ARRAY_DIR}/{len(self.arrays):06d}.npy"
            self.arrays[key] = arr
            self._array_keys[id(arr)] = key
        return {"__array__": key}

    def add_texture(self, tex):
        if id(tex) not in self._texture_ids:
            self._texture_ids[id(tex)] = len(self.textures)
            entry = {"class": _class_path(tex)}
            entry["parameters"] = {
                name: int(getattr(tex, name))
                for name in _TEXTURE_PARAMETERS
                if tex.has_trait(name)
            }
            if isinstance(tex, ColormapTexture):
                entry["colormap_name"] = tex.colormap_name
            elif tex.data is not None:
                entry["data"] = self.add_array(tex.data)
            self.textures.append(entry)
        return {"__texture__": self._texture_ids[id(tex)]}

    def add_data_object(self, data):
        if id(data) not in self._data_ids:
            self._data_ids[id(data)] = len(self.data_objects)
            self.data_objects.append(None)
            self.data_objects[self._data_ids[id(data)]] = data._get_state(self)
        return {"__data__": self._data_ids[id(data)]}

    def encode(self, value):
        """Convert a value into something json can write."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return self.add_array(value)
        if isinstance(value, Texture):
            return self.add_texture(value)
        if isinstance(value, VertexArray):
            return self.encode_vertex_array(value)
        if isinstance(value, (list, tuple)):
            return [self.encode(v) for v in value]
        if isinstance(value, dict):
            if all(isinstance(k, str) for k in value):
                return {k: self.encode(v) for k, v in value.items()}
            return {
                "__items__": [
                    [self.encode(k), self.encode(v)] for k, v in value.items()
                ]
            }
        if hasattr(value, "in_units"):
            # unyt arrays and quantities
            return self.encode(np.asarray(value.d))
        raise TypeError(f"Cannot serialize a value of type {type(value)}")

    def encode_vertex_array(self, va):
        return {
            "__vertex_array__": {
                "name": va.name,
                "each": va.each,
                "indices": self.encode(va.indices),
                "attributes": [
                    {
                        "name": a.name,
                        "divisor": a.divisor,
                        "integer": a.integer,
                        "data": self.encode(a.data),
                    }
                    for a in va.attributes
                ],
            }
        }

    def encode_traits(self, obj):
        """Encode the traits of obj that are tagged with config=True."""
        return {
            name: self.encode(getattr(obj, name))
            for name in sorted(obj.trait_names(config=True))
        }


class SceneReader:
    """Decodes values written by SceneWriter, uploading arrays to the GPU."""

    def __init__(self, archive, state):
        self.archive = archive
        self.state = state
        self._arrays = {}
        self._textures = {}
        self._data_objects = {}

    def get_array(self, key):
        if key not in self._arrays:
            with self.archive.open(key) as f:
                self._arrays[key] = np.lib.format.read_array(f, allow_pickle=False)
        return self._arrays[key]

    def get_texture(self, index):
        if index not in self._textures:
            entry = self.state["textures"][index]
            cls = _import_class(entry["class"])
            tex = cls(**entry["parameters"])
            if "colormap_name" in entry:
                tex.colormap_name = entry["colormap_name"]
            elif "data" in entry:
                tex.data = self.decode(entry["data"])
            self._textures[index] = tex
        return self._textures[index]

    def get_data_object(self, index):
        if index not in self._data_objects:
            entry = self.state["data_objects"][index]
            cls = _import_class(entry["class"])
            self._data_objects[index] = cls._from_state(entry, self)
        return self._data_objects[index]

    def decode(self, value):
        if isinstance(value, list):
            return [self.decode(v) for v in value]
        if not isinstance(value, dict):
            return value
        if "__array__" in value:
            return self.get_array(value["__array__"])
        if "__texture__" in value:
            return self.get_texture(value["__texture__"])
        if "__data__" in value:
            return self.get_data_object(value["__data__"])
        if "__vertex_array__" in value:
            return self.decode_vertex_array(value["__vertex_array__"])
        if "__items__" in value:
            return {
                _hashable(self.decode(k)): self.decode(v) for k, v in value["__items__"]
            }
        return {k: self.decode(v) for k, v in value.items()}

    def decode_vertex_array(self, state):
        va = VertexArray(name=state["name"], each=state["each"])
        indices = self.decode(state["indices"])
        if indices is not None:
            va.indices = indices
        for attr in state["attributes"]:
            va.attributes.append(
                VertexAttribute(
                    name=attr["name"],
                    divisor=attr["divisor"],
                    integer=attr.get("integer", False),
                    data=self.decode(attr["data"]),
                )
            )
        return va

    def restore_traits(self, obj, traits, first=()):
        """Set encoded config traits on obj, setting those in ``first`` first."""
        names = [n for n in first if n in traits]
        names += [n for n in traits if n not in names]
        for name in names:
            setattr(obj, name, self.decode(traits[name]))


def _hashable(value):
    if isinstance(value, list):
        return tuple(_hashable(v) for v in value)
    return value


def save_scene(scene, filename, compress=False):
    """
    Save the state of a SceneGraph to a file.

    Parameters
    ----------
    scene: SceneGraph
        The scene to save.
    filename: str or path-like
        The file to write, a zip archive.
    compress: bool
        Whether to deflate the archive. Texture data often compresses well, but
        compressing and decompressing it takes time.
    """
    writer = SceneWriter()
    for data in scene.data_objects:
        writer.add_data_object(data)
    state = {
        "format_version": FORMAT_VERSION,
        "camera": {
            "class": _class_path(scene.camera),
            "state": writer.encode(scene.camera.dict()),
        },
        "n_scene_data_objects": len(scene.data_objects),
        "components": [c._get_state(writer) for c in scene.components],
        "annotations": [a._get_state(writer) for a in scene.annotations],
    }
    state["data_objects"] = writer.data_objects
    state["textures"] = writer.textures

    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(filename, "w", compression=mode, allowZip64=True) as zf:
        zf.writestr(_SCENE_FILE, json.dumps(state, indent=2))
        for key, arr in writer.arrays.items():
            with zf.open(key, "w", force_zip64=True) as f:
                np.lib.format.write_array(f, arr, allow_pickle=False)


def load_scene(filename, ds=None):
    """
    Load a SceneGraph saved with save_scene.

    This uploads textures and vertex data to the GPU, so an OpenGL context must
    be active (e.g., create the rendering context first).

    Parameters
    ----------
    filename: str or path-like
        The file to read.
    ds: yt Dataset, optional
        A dataset to attach to the scene graph. This is not needed to render
        the scene.

    Returns
    -------
    scene: SceneGraph
    """
    from yt_idv.scene_graph import SceneGraph

    with zipfile.ZipFile(filename, "r") as zf:
        state = json.loads(zf.read(_SCENE_FILE))
        version = state.get("format_version")
        if version != FORMAT_VERSION:
            raise ValueError(
                f"Unsupported scene file version {version} (expected {FORMAT_VERSION})"
            )
        reader = SceneReader(zf, state)

        camera_cls = _import_class(state["camera"]["class"])
        camera = camera_cls()
        camera.update_from_dict(reader.decode(state["camera"]["state"]))

        scene = SceneGraph(camera=camera)
        if ds is not None:
            scene.ds = ds
        scene.data_objects = [
            reader.get_data_object(i) for i in range(state["n_scene_data_objects"])
        ]
        scene.components = [
            _component_from_state(e, reader) for e in state["components"]
        ]
        scene.annotations = [
            _component_from_state(e, reader) for e in state["annotations"]
        ]
    return scene


def _component_from_state(entry, reader):
    cls = _import_class(entry["class"])
    return cls._from_state(entry, reader)


class SerializableMixin:
    """
    Saves the traits tagged ``config=True`` and the attributes named in
    ``_saved_attributes`` (which may hold arrays, textures or vertex arrays).
    """

    _saved_attributes = ()
    # config traits with observers that change other config traits
    _restore_first = ()

    def _get_state(self, writer):
        # attribute defaults can set config traits, so encode these first
        attrs = {}
        for name in self._saved_attributes:
            value = getattr(self, name, traitlets.Undefined)
            if value is not traitlets.Undefined:
                attrs[name] = writer.encode(value)
        return {
            "class": _class_path(self),
            "traits": writer.encode_traits(self),
            "attributes": attrs,
        }

    def _set_state(self, state, reader):
        for name, value in state["attributes"].items():
            setattr(self, name, reader.decode(value))
        reader.restore_traits(self, state["traits"], first=self._restore_first)

    @classmethod
    def _from_state(cls, state, reader):
        obj = cls()
        obj._set_state(state, reader)
        return obj
