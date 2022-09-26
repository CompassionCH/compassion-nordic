"""File parsers for Bg AutoGiro and OCR Giro files."""

from typing import List

from .converters import *
from .objects import *
from . import  enums, objects  # isort: skip

__version__ = '1.0.0'

__all__: List[str] = enums.__all__ + objects.__all__


