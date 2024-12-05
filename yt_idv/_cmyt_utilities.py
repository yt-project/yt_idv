import cmyt
from matplotlib.colors import Colormap

# we want to display colormap name then cmyt for sorting purposes
cmyt_names = [
    f"{cm}.cmyt" for cm in dir(cmyt) if isinstance(getattr(cmyt, cm), Colormap)
]


def validate_cmyt_name(cm):
    if cm.endswith(".cmyt"):
        return "cmyt." + cm.split(".")[0]
    return cm
