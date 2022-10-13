##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#    Inspired by Netsgiro structure
##############################################################################

from typing import Any, Callable

from attr import Attribute
from attr.validators import instance_of

C = Callable[[object, Attribute, Any], None]


def str_of_length(length: int) -> C:
    """Validate that the value is a string of the given length."""

    def validator(instance: object, attribute: Attribute, value: Any) -> None:
        instance_of(str)(instance, attribute, value)
        if len(value) != length:
            raise ValueError(f'{attribute.name} must be exactly {length} chars, got {value!r}')

    return validator
