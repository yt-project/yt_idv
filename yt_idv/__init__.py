"""Top-level package for interactive volume rendering for yt."""

__author__ = """Matthew Turk"""
__email__ = "matthewturk@gmail.com"
__version__ = "0.2.0"

import os

# We don't want to import this if we're just doing offscreen rendering
from .rendering_contexts import render_context
