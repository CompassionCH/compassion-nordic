"""Enums for all codes used in OCR files."""

from enum import IntEnum
from typing import List

__all__: List[str] = [
    'RecordType',
    'SignCode',
]


class SignCode(IntEnum):
    NO_AMOUNT = 0
    COLLECTION = 1
    DISBURSEMENT = 2


class RecordType(IntEnum):
    DATA_DELIVERY_START = 2
    SECTION_START = 12
    PAYMENT_INFO = 42
    TEXT_TO_DEBTOR = 52
    SECTION_END = 92
    DATA_DELIVERY_END = 992
