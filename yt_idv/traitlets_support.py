import matplotlib.font_manager
import numpy as np
import traitlets


class YTPositionTrait(traitlets.TraitType):
    default_value = None
    info_text = "A position in code_length"

    def validate(self, obj, value):
        if isinstance(value, (tuple, list)):
            value = np.array(value)
        if hasattr(value, "in_units"):
            value = value.in_units("unitary").d
        if not isinstance(value, np.ndarray):
            self.error(obj, value)
        return value.astype("f4")


def ndarray_shape(*dimensions):
    # http://traittypes.readthedocs.io/en/latest/api_documentation.html
    def validator(trait, value):
        if value.shape != dimensions:
            raise traitlets.TraitError(
                "Expected an of shape %s and got and array with shape %s"
                % (dimensions, value.shape)
            )
        else:
            return value

    return validator


def ndarray_ro():
    def validator(trait, value):
        if value.flags["WRITEABLE"]:
            value = value.copy()
            value.flags["WRITEABLE"] = False
        return value

    return validator


class FontTrait(traitlets.TraitType):
    info_text = "A font instance from matplotlib"

    def validate(self, obj, value):
        if isinstance(value, str):
            try:
                font_fn = matplotlib.font_manager.findfont(value)
                value = matplotlib.font_manager.get_font(font_fn)
            except FileNotFoundError:
                self.error(obj, value)
        return value


class ArrayTrait(traitlets.TraitType):

    # a replacement for the un-maintained traittypes.Array
    info_text = "A numpy array"

    def __init__(self, default_value=None, **kwargs):
        if default_value is not None:
            default_value = np.asarray(default_value)
        super().__init__(default_value=default_value, **kwargs)
        self.validators = []

    def valid(self, *args):
        self.validators.extend(args)
        return self

    def validate(self, obj, value):
        if not isinstance(value, np.ndarray):
            value = np.asarray(value)

        for validator in self.validators:
            value = validator(obj, value)

        if not isinstance(value, np.ndarray):
            self.error(obj, value)

        return value
