import numpy as np
import traitlets

from yt_idv.traitlets_support import ArrayTrait, ndarray_shape


def test_array_trait():

    shp = (4, 3)
    x = np.ones(shp)

    def extra(obj, value):
        # arbitrary to make sure the logic is working
        return value * 2.0

    class UsefulTestClass(traitlets.HasTraits):

        array_no_args = ArrayTrait(allow_none=True)
        array_with_default = ArrayTrait(x)
        array_with_default_valid = ArrayTrait(x).valid(ndarray_shape(*shp))
        two_x = ArrayTrait(x).valid(extra)
        two_x_chained = ArrayTrait(x).valid(ndarray_shape(*shp), extra)

    utc = UsefulTestClass()
    assert utc.array_no_args is None
    assert np.all(utc.array_with_default == x)
    assert np.all(utc.array_with_default_valid == x)
    assert np.all(utc.two_x == 2 * x)
    assert np.all(utc.two_x_chained == 2 * x)
