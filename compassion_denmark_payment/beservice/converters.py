"""Custom converters for :mod:`attrs`."""
import datetime
from typing import Optional, TypeVar, Union

from .enums import (
    SignCode,
    RecordType,
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


def to_sign_code(value: Union[SignCode, int, str]) -> SignCode:
    """Convert input to TransactionType."""
    return SignCode(int(value))


def to_date(value: Union[datetime.date, str]) -> datetime.date:
    """Convert input to date."""
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(value, '%d%m%Y').date()


def to_date_short_or_none(value: Union[datetime.date, str]) -> Optional[Union[datetime.date, None]]:
    """Convert input to date or None."""
    if isinstance(value, str) and '000000' in value:
        return None if '000000' in value else datetime.datetime.strptime(value, '%d%m%y').date()
    return value


def to_date_long_or_none(value: Union[datetime.date, str]) -> Optional[Union[datetime.date, None]]:
    """Convert input to date or None."""
    if isinstance(value, str) and '00000000' in value:
        return None if '00000000' in value else datetime.datetime.strptime(value, '%d%m%Y').date()
    return value
