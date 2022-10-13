##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#    Inspired by Netsgiro structure
##############################################################################
from enum import IntEnum
from typing import List

__all__: List[str] = [
    'TransactionType',
    'PeriodCode',
    'PaymentStatus'
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
    END_RECORD = 9


class PaymentStatus(IntEnum):
    """Assignment types tell what type of transaction this is."""

    APPROVED = 0
    INSUFFICIENT_FUNDS = 1
    NO_CONNECTION = 2
    RENEWED_FUNDS = 9
