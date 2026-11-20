"""Motor/propeller noise removal and ambient noise level estimation.

Owner: colleague. Add new filters as separate files in this folder and
export the one to use here.
"""
from .passthrough import PassThroughFilter

__all__ = ["PassThroughFilter"]
