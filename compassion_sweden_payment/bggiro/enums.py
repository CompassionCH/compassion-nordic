"""Enums for all codes used in OCR files."""

from enum import IntEnum
from typing import List

__all__: List[str] = [
    'TransactionType',
    'PeriodCode',
]


class PeriodCode(IntEnum):
    ONCE = 0
    # The calendar day specified in the payment record, if it is a bank day. Otherwise, the next bank day.
    ONCE_A_MONTH_SPECIFIC = 1
    ONCE_A_QUARTER_SPECIFIC = 2
    TWICE_A_YEAR_SPECIFIC = 3
    ONCE_A_YEAR_SPECIFIC = 4
    # The last calendar day of the month, if it is a bank day. Otherwise, the previous bank day.
    ONCE_A_MONTH_LAST = 5
    ONCE_A_QUARTER_LAST = 6
    TWICE_A_YEAR_LAST = 7
    ONCE_A_YEAR_LAST = 8


class TransactionType(IntEnum):
    """Assignment types tell what type of transaction this is."""

    OPENING_RECORD = 1
    INCOMING_PAYMENT = 82
    OUTGOING_PAYMENT = 32
