# This module is just a handful of functions to pack textures into an atlas.
# The end goal is to minimize the used memory, but to maximize the fill of that
# memory.  If we get an optimal-ish texture atlas, we can proceed to use that
# instead of either bindless textures *or* lots of tiny textures, which in
# theory should save us a ton of memory and time.  We won't have to bind
# textures one-by-one anymore, and we also won't have to use all that extra
# space that gets allocated for small texture blocks.

import numpy as np

def pack(sizes, padding = 0):
    """
    Given a set of sizes, and a padding to be applied to each, find the best
    layout for them. Sizes should be a list of dimensions and padding an
    integer.  It returns the offsets into an atlas of size dims.
    """
    # We want to place them first in z, then y, then x
    if len(sizes) == 0: return (np.empty((0,3), dtype="int64"), np.array([0,0,0]))
    sizes = np.asarray(sizes, dtype="int64")
    if (sizes <= 0).any(): raise ValueError
    order = np.lexsort((-sizes[:,0], -sizes[:,1], -sizes[:,2]))
    psizes = (sizes[order] + 2 * padding) # We'll offset later
    max_size = psizes.prod(axis=1).sum()**(1/3)
    max_size = max(max_size, psizes.max())
    psizes = psizes.tolist()
    results = []
    for factor in [0.85, 0.9, 1.1, 1.3]:
        offsets, dims = _pack_with_size(psizes, int(max_size * factor))
        results.append( (dims.prod(), offsets, dims) )
    results.sort(key = lambda a: a[0])
    _, placed, dims = results[0]
    offsets = np.zeros(sizes.shape, dtype="int64")
    offsets[order] = placed
    return offsets + padding, dims

def _pack_with_size(psizes, max_size):
    """

    """
    # This breaks if it's not sorted.
    dims = np.zeros(3, dtype="int64")
    current_i = current_j = current_k = 0
    _, size_y, size_z = psizes[0]
    placed = []
    for ps in psizes:
        size_x = ps[0]
        # If this pushes us past our bounds along x, we go to the next j
        if current_i + size_x > max_size:
            current_i = 0
            current_j += size_y
            # Reset our current height
            size_y = 0
        # Same, if this pushes us beyond bounds in y, we go to next k as well
        # as resetting i.
        if current_j + max(size_y, ps[1]) > max_size:
            current_i = 0
            current_j = 0
            current_k += size_z
            size_y = 0
            size_z = ps[2] # always monotonic as it's primary
        if current_k + size_z > 2048:
            raise RuntimeError
        placed.append( (current_i, current_j, current_k) )
        size_y = max(size_y, ps[1])
        current_i += size_x
    offsets = np.array(placed, dtype="int64")
    dims = (offsets + psizes).max(axis=0)
    return offsets, dims
