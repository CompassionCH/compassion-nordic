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
    'RecordType',
    'SignCode',
    'DeliveryType',
    'SectionType',
    'TransactionCode'
]


class SignCode(IntEnum):
    NO_AMOUNT = 0
    COLLECTION = 1
    DISBURSEMENT = 2


class RecordType(IntEnum):
    DATA_DELIVERY_START = 2
    SECTION_START = 12
    INFO = 42
    TEXT_TO_DEBTOR = 52
    SECTION_END = 92
    DATA_DELIVERY_END = 992


class TransactionCode(IntEnum):

    ACTIVE_MANDATE = 230
    MANDATE_REGISTERED = 231
    MANDATE_CANCELLED_BY_BANK = 232
    MANDATE_CANCELLED_BY_CREDITOR = 233
    MANDATE_CANCELLED_BY_BETALINGSSERVICE = 234

    AUTOMATED_PAYMENT_COMPLETED = 236
    AUTOMATED_PAYMENT_REJECTED = 237
    AUTOMATED_PAYMENT_CANCELLED = 238
    AUTOMATED_PAYMENT_CHARGED_BACK = 239

    COLLECTION_INFORMATION = 280


class DeliveryType(IntEnum):
    COLLECTION_DATA = 601
    PAYMENT_INFORMATION = 602
    MANDATE_INFORMATION = 603


class SectionType(IntEnum):
    ACTIVE_MANDATE = 210
    REGISTERED_AND_CANCELLED_MANDATE = 212

    AUTOMATED_PAYMENT_INFORMATION = 211
    SLIP_PAYMENT_INFORMATION = 215

    COLLECTION = 112
