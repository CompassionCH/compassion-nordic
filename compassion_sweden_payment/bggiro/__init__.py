##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#    Inspired by Netsgiro structure

from typing import List

from .converters import *
from .objects import *
from . import  enums, objects  # isort: skip

__version__ = '1.0.0'

__all__: List[str] = enums.__all__ + objects.__all__
