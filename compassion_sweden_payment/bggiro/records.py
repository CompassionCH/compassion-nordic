"""The lower-level records API."""

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
    cast,
)
import datetime
from attrs import define, field

from .converters import (
    to_date,
    to_date_or_genast,
    to_safe_str_or_none,
    to_transaction_type, to_period_code, number_recurring_payments_to_int,
)
from .validators import str_of_length

if TYPE_CHECKING:
    import datetime

from .enums import TransactionType, PeriodCode

__all__: List[str] = [
    'OpeningRecord',
    'PaymentRecord',
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
    payer_bankgiro_number: str = field(validator=str_of_length(10))
    date_written: 'datetime.date' = field(converter=to_date)

    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            01      # Transaction Code
            (?P<date_written>\d{8})
            AUTOGIRO# LayoutName
            [ ]{44}   # Padding
            (?P<customer_number>\d{6})
            (?P<payer_bankgiro_number>\d{10})
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
                + (' ' * 44) +
                f'{self.customer_number:6}{self.payer_bankgiro_number:10}'
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
    payee_bankgiro_number: int = field(converter=int)
    amount: int = field(converter=int)
    reference: str = field(converter=to_safe_str_or_none)
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
            (?P<payee_bankgiro_number>\d{10})
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
            (?P<payee_bankgiro_number>\d{10})
            (?P<reference>.{12,16})
            [ ]{0,11}
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
                  f'{self.payee_bankgiro_number:010d}'
                  f'{self.reference:16}'
                + ' '
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
                      TransactionType.OPENING_RECORD: OpeningRecord
                      }

    results: List[R] = []

    for line in data.strip().splitlines():
        # if len(line) != 80:
        #     raise ValueError('All lines must be exactly 80 chars long')

        record_type_str = line[:2]
        if not record_type_str.isnumeric():
            raise ValueError(f'Record type must be numeric, got {record_type_str!r}')

        record_type = to_transaction_type(record_type_str)
        record_cls = record_classes[record_type]

        results.append(record_cls.from_string(line))

    return results
