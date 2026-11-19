import traitlets

from yt_idv.scene_components.blocks import BlockRendering
from yt_idv.scene_data.octree_block_collection import OctreeBlockCollection


class OctreeBlockRendering(BlockRendering):
    """
    Renders an :class:`~yt_idv.scene_data.octree_block_collection.OctreeBlockCollection`.

    Octree blocks are rendered exactly as grid blocks are, so this is a
    :class:`~yt_idv.scene_components.blocks.BlockRendering` that only checks
    the type of its data.
    """

    data = traitlets.Instance(OctreeBlockCollection)
