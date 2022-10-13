##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#    Inspired by Netsgiro structure
##############################################################################

import datetime
from typing import Optional, TypeVar, Union

from .enums import (
    SignCode,
    RecordType,
    DeliveryType,
    SectionType,
    TransactionCode,
)

T = TypeVar('T')


def number_recurring_payments_to_int(value: Union[None, int, str]) -> int:
    if isinstance(value, str):
        return 0 if not value.isnumeric() else int(value)
    if isinstance(value, int):
        return value


def to_int_or_none(value: Union[None, int, str]) -> Optional[int]:
    """Convert input to int or None."""
    if isinstance(value, str):
        return None if not value.isnumeric() else int(value)
    return value


def to_safe_str_or_none(value: Optional[str]) -> Optional[str]:
    """Convert input to cleaned string or None."""
    if value is None:
        return None
    v = str(value.strip()).replace('\r', '').replace('\n', '')
    return v or None


def to_record_type(value: Union[RecordType, int, str]) -> RecordType:
    """Convert input to TransactionType."""
    return RecordType(int(value))


def to_sign_code(value: Union[SignCode, int, str]) -> Optional[SignCode]:
    """Convert input to TransactionType."""
    if value is None:
        return None
    return SignCode(int(value))


def to_delivery_type(value: Union[SignCode, int, str]) -> DeliveryType:
    """Convert input to TransactionType."""
    return DeliveryType(int(value))


def to_section_type(value: Union[SignCode, int, str]) -> SectionType:
    """Convert input to TransactionType."""
    return SectionType(int(value))


def to_transaction_code(value: Union[SignCode, int, str]) -> TransactionCode:
    """Convert input to TransactionType."""
    return TransactionCode(int(value))


def to_date(value: Union[datetime.date, str]) -> datetime.date:
    """Convert input to date."""
    if isinstance(value, datetime.date):
        return value
    date_format = '%d%m%Y' if len(value) == 8 else '%d%m%y'
    return datetime.datetime.strptime(value, date_format).date()


def to_date_or_none(value):
    """Convert input to date or None."""
    if isinstance(value, str):
        if '000000' in value:
            return None
        elif len(value) == 6:
            return datetime.datetime.strptime(value, '%d%m%y').date()
        elif len(value) == 8:
            return datetime.datetime.strptime(value, '%d%m%Y').date()
        else:
            raise ValueError(f'Error in date parsing  {value}')
    return value
