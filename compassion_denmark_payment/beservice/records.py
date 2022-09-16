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
import netsgiro
import datetime
from attrs import define, field

from .converters import (
    to_date,
    to_date_short_or_none,
    to_date_long_or_none,
    to_int_or_none,
    to_safe_str_or_none,
    to_sign_code, number_recurring_payments_to_int, to_record_type,
)
from .validators import str_of_length

if TYPE_CHECKING:
    import datetime

from .enums import SignCode, RecordType

__all__: List[str] = [
    'DataDeliveryStartRecord',
    'SectionStartRecord',
    'PaymentInfoRecord',
    'TextToDebtorRecord',
    'SectionEndRecord',
    'DataDeliveryEndRecord',
    'parse',
]

R = TypeVar('R', bound='Record')


@define
class Record(ABC):
    """Record base class."""
    RECORD_TYPE: ClassVar[RecordType]
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
class DataDeliveryStartRecord(Record):
    """TransmissionStart is the first record in every OCR file.

    A file can only contain a single transmission.

    Each transmission can contain any number of assignments.
    """

    data_supplier_number: int = field(converter=int)
    subsystem: str = field(validator=str_of_length(3))
    delivery_identification: int = field(converter=int)
    date: Union[datetime.date, None] = field(converter=to_date_short_or_none)

    RECORD_TYPE = RecordType.DATA_DELIVERY_START
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            002 # Data Record Type
            (?P<data_supplier_number>\d{8})
            (?P<subsystem>.{3})
            0601# Delivery Type
            (?P<delivery_identification>\d{10})
            [ ]{19}
            (?P<date>\d{6})
            [ ]{0,73}
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS002'
                + f'{self.data_supplier_number:08d}{self.subsystem:3}'
                + f'0601'
                + f'{self.delivery_identification:010d}'
                + (' ' * 19)
                + (self.date and f'{self.date:%y%m%d}' or ('0' * 6))
                + (' ' * 72)
        )


@define
class SectionStartRecord(Record):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    data_supplier_id: str = field(converter=to_safe_str_or_none)
    date: Union[datetime.date, None] = field(converter=to_date_long_or_none)
    main_text_line: str = field(converter=to_safe_str_or_none)

    RECORD_TYPE = RecordType.SECTION_START
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            012 # Data Record Type
            (?P<pbs_number>\d{8})
            0112 # Section Number
            [ ]{5}
            (?P<debtor_group_number>\d{5})
            (?P<data_supplier_id>.{15})
            [ ]{4}
            (?P<date>\d{8})
            [ ]{0,14}
            (?P<main_text_line>.{60})
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS012'
                + f'{self.pbs_number:08d}'
                + f'0112'
                + ' ' * 4
                + f'{self.debtor_group_number:05d}'
                + (self.data_supplier_id and f'{self.data_supplier_id:15}' or (' ' * 15))
                + (' ' * 4)
                + (self.date and f'{self.date:%Y%m%d}' or ('0' * 8))
                + (' ' * 14)
                + (self.main_text_line and f'{self.main_text_line:60}' or (' ' * 60))
        )


@define
class PaymentInfoRecord(Record):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    customer_number: str = field(validator=str_of_length(15))
    mandate_number: int = field(converter=int)
    payment_date: datetime.date = field(converter=to_date)
    sign_code: 'SignCode' = field(converter=to_sign_code)
    amount: int = field(converter=int)
    reference: str = field(converter=to_safe_str_or_none)
    payer_id: int = field(converter=to_int_or_none)

    RECORD_TYPE = RecordType.PAYMENT_INFO
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            042 # Data Record Type
            (?P<pbs_number>\d{8})
            0280 # Section Number
            00000
            (?P<debtor_group_number>\d{5})
            (?P<customer_number>.{15})
            (?P<mandate_number>\d{9})
            (?P<payment_date>\d{8})
            (?P<sign_code>\d{1})
            (?P<amount>\d{13})
            (?P<reference>.{30})
            00
            (?P<payer_id>.{15})
            0{8}
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS042'
                + f'{self.pbs_number:08d}'
                + f'0280'
                + f'00000'
                + f'{self.debtor_group_number:05d}'
                + f'{self.customer_number:15}'
                + f'{self.mandate_number:09d}'
                + f'{self.payment_date:%d%m%Y}'
                + f'{self.sign_code:01d}'
                + f'{self.amount:013d}'
                + (self.reference and f'{self.reference:30}' or (' ' * 30))
                + '00'
                + (self.payer_id and f'{self.payer_id:15}' or (' ' * 15))
                + ('0' * 8)
        )


@define
class TextToDebtorRecord(Record):
    pbs_number: int = field(converter=int)
    data_record_num: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    customer_number: str = field(validator=str_of_length(15))
    mandate_number: int = field(converter=int)
    text_line: str = field()

    RECORD_TYPE = RecordType.TEXT_TO_DEBTOR
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            052 # Data Record Type
            (?P<pbs_number>\d{8})
            0241 # Transaction Code
            (?P<data_record_num>\d{5})
            (?P<debtor_group_number>\d{5})
            (?P<customer_number>.{15})
            (?P<mandate_number>\d{9})
            [ ]{1}
            (?P<text_line>.{60})
            [ ]{16}
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS052'
                + f'{self.pbs_number:08d}'
                + f'0241'
                + f'{self.data_record_num:05d}'
                + f'{self.debtor_group_number:05d}'
                + f'{self.customer_number:15}'
                + f'{self.mandate_number:09d}'
                + ' '
                + f'{self.text_line:60}'
                + (' ' * 16)
        )


@define
class SectionEndRecord(Record):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    num_of_record_42: int = field(converter=int)
    net_amount: int = field(converter=int)
    num_of_record_52_62: int = field(converter=int)
    num_of_record_22: int = field(converter=int)

    RECORD_TYPE: ClassVar[RecordType] = RecordType.SECTION_END
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            092 # Data Record Type
            (?P<pbs_number>\d{8})
            0112 # Transaction Code
            00000
            (?P<debtor_group_number>\d{5})
            [ ]{4}
            (?P<num_of_record_42>\d{11})
            (?P<net_amount>\d{15})
            (?P<num_of_record_52_62>\d{11})
            [ ]{15}
            (?P<num_of_record_22>\d{11})
            [ ]{34}
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS092'
                + f'{self.pbs_number:08d}'
                + f'0112'
                + f'00000'
                + f'{self.debtor_group_number:05d}'
                + (' ' * 4)
                + f'{self.num_of_record_42:011d}'
                + f'{self.net_amount:015d}'
                + f'{self.num_of_record_52_62:011d}'
                + (' ' * 15)
                + f'{self.num_of_record_22:011d}'
                + (' ' * 34)
        )


@define
class DataDeliveryEndRecord(Record):
    data_supplier_number: int = field(converter=int)
    subsystem: str = field(validator=str_of_length(3))
    num_of_section: int = field(converter=int)
    num_of_record_42: int = field(converter=int)
    net_amount: int = field(converter=int)
    num_of_record_52_62: int = field(converter=int)
    num_of_record_22: int = field(converter=int)

    RECORD_TYPE: ClassVar[RecordType] = RecordType.DATA_DELIVERY_END
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            992 # Data Record Type
            (?P<data_supplier_number>\d{8})
            (?P<subsystem>.{3})
            0601# Delivery Type
            (?P<num_of_section>\d{11})
            (?P<num_of_record_42>\d{11})
            (?P<net_amount>\d{15})
            (?P<num_of_record_52_62>\d{11})
            0{15}
            (?P<num_of_record_22>\d{11})
            0{34}
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        return (
                f'BS992'
                + f'{self.data_supplier_number:08d}'
                + f'{self.subsystem:3}'
                + f'0601'
                + f'{self.num_of_section:011d}'
                + f'{self.num_of_record_42:011d}'
                + f'{self.net_amount:015d}'
                + f'{self.num_of_record_52_62:011d}'
                + ('0' * 15)
                + f'{self.num_of_record_22:011d}'
                + ('0' * 34)
        )


def parse(data: str) -> List[R]:
    """Parse an OCR file into a list of record objects."""

    def all_subclasses(cls: Union[Type[R], Type[Record]]) -> List[Type[R]]:
        """Return a list of subclasses for a given class."""
        classes = cls.__subclasses__() + [
            subsubcls for subcls in cls.__subclasses__() for subsubcls in all_subclasses(subcls)
        ]
        return cast(List[Type[R]], classes)

    record_classes = {
        cls.RECORD_TYPE: cls for cls in all_subclasses(Record) if hasattr(cls, 'RECORD_TYPE')
    }

    results: List[R] = []

    for line in data.strip().splitlines():
        line = line + ' ' * (128 - len(line))
        # if len(line) != 80:
        #     raise ValueError('All lines must be exactly 80 chars long')

        record_type_str = line[2:5]
        if not record_type_str.isnumeric():
            raise ValueError(f'Record type must be numeric, got {record_type_str!r}')

        record_type = to_record_type(record_type_str)
        record_cls = record_classes[record_type]

        results.append(record_cls.from_string(line))

    return results
