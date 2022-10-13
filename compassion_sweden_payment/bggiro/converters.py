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
    PeriodCode,
    TransactionType,
    PaymentStatus
)

T = TypeVar('T')


def number_recurring_payments_to_int(value: Union[None, int, str]) -> int:
    if isinstance(value, str):
        return 0 if not value.isnumeric() else int(value)
    if isinstance(value, int):
        return value


def to_payment_status(value: Union[None, int, str]) -> PaymentStatus:
    if value is None or value == ' ':
        return PaymentStatus.APPROVED
    else:
        return PaymentStatus(int(value))


def to_safe_str_or_none(value: Optional[str]) -> Optional[str]:
    """Convert input to cleaned string or None."""
    if value is None:
        return None
    v = str(value.strip()).replace('\r', '').replace('\n', '')
    return v or None


def to_int_or_none(value: Optional[Union[str, int]]) -> Optional[int]:
    """Convert input to cleaned string or None."""
    if value is None:
        return None
    return int(value)


def to_transaction_type(value: Union[TransactionType, int, str]) -> TransactionType:
    """Convert input to TransactionType."""
    return TransactionType(int(value))


def to_period_code(value: Union[PeriodCode, int, str]) -> PeriodCode:
    """Convert input to TransactionType."""
    return PeriodCode(int(value))


def to_date(value: Union[datetime.date, str]) -> datetime.date:
    """Convert input to date."""
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(value, '%Y%m%d').date()


def to_date_or_genast(value: Union[datetime.date, str]) -> Optional[Union[datetime.date, str]]:
    """Convert input to date or None."""
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and 'GENAST' in value:
        return 'GENAST  '
    return datetime.datetime.strptime(value, '%Y%m%d').date()
