##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#    Inspired by Netsgiro structure
##############################################################################

import re
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    ClassVar,
    List,
    Pattern,
    Type,
    TypeVar,
    Union,
    cast, Optional,
)
import datetime
from attrs import define, field

from .converters import (
    to_date,
    to_date_or_genast,
    to_safe_str_or_none,
    to_transaction_type,
    to_period_code,
    number_recurring_payments_to_int,
    to_payment_status, to_int_or_none
)
from .validators import str_of_length

if TYPE_CHECKING:
    import datetime

from .enums import TransactionType, PeriodCode, PaymentStatus

__all__: List[str] = [
    'OpeningRecord',
    'PaymentRecord',
    'EndRecord',
    'Record',
    'parse',
]

R = TypeVar('R', bound='Record')


@define
class Record(ABC):
    """Record base class."""

    _PATTERNS: ClassVar[List[Pattern]]

    @classmethod
    def from_string(cls: Type[R], line: str) -> R:
        """Parse OCR string into a record object."""
        for pattern in cls._PATTERNS:
            matches = pattern.match(line)
            if matches is not None:
                return cls(**matches.groupdict())

        raise ValueError(f'{line!r} did not match {cls.__name__} record formats')

    @abstractmethod
    def to_ocr(self) -> str:
        """Get record as OCR string."""


@define
class OpeningRecord(Record):
    """TransmissionStart is the first record in every OCR file.

    A file can only contain a single transmission.

    Each transmission can contain any number of assignments.
    """

    customer_number: str = field(validator=str_of_length(6))
    payee_bankgiro_number: str = field(validator=str_of_length(10))
    date_written: 'datetime.date' = field(converter=to_date)
    clearing_number: Optional[int] = field(default=None, converter=to_int_or_none)
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            01      # Transaction Code
            (?P<date_written>\d{8})
            AUTOGIRO# LayoutName
            [ ]{44}   # Padding
            (?P<customer_number>\d{6})
            (?P<payee_bankgiro_number>\d{10})
            [ ]{2} 
            $ 
            ''',
            re.VERBOSE,
        ),
        re.compile(
            r'''
            ^
            01      # Transaction Code
            (?P<date_written>\d{8})
            AUTOGIRO# LayoutName
            (?P<clearing_number>9900)
            [ ]{40}   # Padding
            (?P<customer_number>\d{6})
            (?P<payee_bankgiro_number>\d{10})
            [ ]{0,2} 
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'01'
                f'{self.date_written:%Y%m%d}'
                f'AUTOGIRO'
                + (self.clearing_number and f'{self.clearing_number:04d}' or (' ' * 4))
                + (' ' * 40) +
                f'{self.customer_number:6}{self.payee_bankgiro_number:10}'
                + (' ' * 2)
        )


@define
class PaymentRecord(Record):
    """AssignmentStart is the first record of an assignment.

    Each assignment can contain any number of transactions.
    """

    transaction_type: 'TransactionType' = field(converter=to_transaction_type)
    payment_date: Union[datetime.date, str] = field(converter=to_date_or_genast)
    period_code: 'PeriodCode' = field(converter=to_period_code)
    number_recurring_payments: int = field(converter=number_recurring_payments_to_int)
    payer_number: int = field(converter=int)
    payer_bankgiro_number: int = field(converter=int)
    amount: int = field(converter=int)
    reference: str = field(converter=to_safe_str_or_none)
    payment_status_code: Optional['PaymentStatus'] = field(default=None, converter=to_payment_status)
    # Only for assignment_type == AssignmentType.TRANSACTIONS
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            (?P<transaction_type>(82|32))
            (?P<payment_date>GENAST  )
            (?P<period_code>0)
            ' '{4}
            (?P<payer_number>\d{16})     # Record type
            (?P<amount>\d{12})
            (?P<payer_bankgiro_number>\d{10})
            (?P<reference>.{16})
            ' '{11}   # Filler
            $
            ''',
            re.VERBOSE,
        ),
        re.compile(
            r'''
            ^
            (?P<transaction_type>(82|32))
            (?P<payment_date>\d{8})
            (?P<period_code>\d{1})
            (?P<number_recurring_payments>.{3})
            [ ]
            (?P<payer_number>\d{16})     # Record type
            (?P<amount>\d{12})
            (?P<payer_bankgiro_number>\d{10})
            (?P<reference>.{16})
            [ ]{10}
            (?P<payment_status_code>.{1})
            $
            ''',
            re.VERBOSE,
        ),
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'{self.transaction_type:02d}'
                + (isinstance(self.payment_date, str) and f'{self.payment_date}' or f'{self.payment_date:%Y%m%d}')
                + f'{self.period_code:01d}'
                + (self.number_recurring_payments and f'{self.number_recurring_payments:03d}' or (' ' * 3))
                + ' '
                + f'{self.payer_number:16d}'
                  f'{self.amount:012d}'
                  f'{self.payer_bankgiro_number:010d}'
                  f'{self.reference:16}'
                + (' ' * 10)
                + (self.payment_status_code and f'{self.payment_status_code:01d}' or (' ' * 1))
        )


@define
class EndRecord(Record):
    """TransmissionStart is the first record in every OCR file.

    A file can only contain a single transmission.

    Each transmission can contain any number of assignments.
    """

    date_written: 'datetime.date' = field(converter=to_date)
    total_amount_outgoing: int = field(converter=int)
    total_number_outgoing: int = field(converter=int)
    total_amount_incoming: int = field(converter=int)
    total_number_incoming: int = field(converter=int)
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            09      # Transaction Code
            (?P<date_written>\d{8})
            9900# Clearing number
            [ ]{14}   # Padding
            (?P<total_amount_outgoing>\d{12})
            (?P<total_number_outgoing>\d{6})
            (?P<total_number_incoming>\d{6})
            0{4}
            (?P<total_amount_incoming>\d{12})
            0{12}
            $ 
            ''',
            re.VERBOSE,
        ),
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'09'
                f'{self.date_written:%Y%m%d}'
                f'9900'
                + (' ' * 14) +
                f'{self.total_amount_outgoing:012d}'
                f'{self.total_number_outgoing:06d}'
                f'{self.total_number_incoming:06d}'
                + ('0' * 4) +
                f'{self.total_amount_incoming:012d}'
                + ('0' * 12)
        )


def parse(data: str) -> List[R]:
    """Parse an OCR file into a list of record objects."""

    def all_subclasses(cls: Union[Type[R], Type[Record]]) -> List[Type[R]]:
        """Return a list of subclasses for a given class."""
        classes = cls.__subclasses__() + [
            subsubcls for subcls in cls.__subclasses__() for subsubcls in all_subclasses(subcls)
        ]
        return cast(List[Type[R]], classes)

    record_classes = {TransactionType.INCOMING_PAYMENT: PaymentRecord,
                      TransactionType.OUTGOING_PAYMENT: PaymentRecord,
                      TransactionType.OPENING_RECORD: OpeningRecord,
                      TransactionType.END_RECORD: EndRecord
                      }

    results: List[R] = []

    for line in data.strip().splitlines():
        line = line + ' ' * (80 - len(line))
        # if len(line) != 80:
        #     raise ValueError('All lines must be exactly 80 chars long')

        record_type_str = line[:2]
        if not record_type_str.isnumeric():
            raise ValueError(f'Record type must be numeric, got {record_type_str!r}')

        record_type = to_transaction_type(record_type_str)
        record_cls = record_classes[record_type]

        results.append(record_cls.from_string(line))

    return results
