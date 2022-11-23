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
    to_int_or_none,
    to_safe_str_or_none,
    to_sign_code, to_record_type, to_delivery_type, to_section_type, to_date_or_none,
    to_transaction_code,
)
from .validators import str_of_length

if TYPE_CHECKING:
    import datetime

from .enums import SignCode, RecordType, DeliveryType, SectionType, TransactionCode

__all__: List[str] = [
    'Record',
    'DataDeliveryStartRecord',
    'SectionStartRecord',
    'InfoRecord',
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
    delivery_type: 'DeliveryType' = field(converter=to_delivery_type)
    delivery_date: Union['datetime.date', None] = field(converter=to_date_or_none)

    RECORD_TYPE = RecordType.DATA_DELIVERY_START
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            002 # Data Record Type
            (?P<data_supplier_number>\d{8})
            (?P<subsystem>.{3})
            (?P<delivery_type>\d{4})# Data Delivery Type
            (?P<delivery_identification>\d{10})
            [ ]{19}
            (?P<delivery_date>\d{6})
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
                + f'{self.delivery_type:04d}'
                + f'{self.delivery_identification:010d}'
                + (' ' * 19)
                + (self.delivery_date and f'{self.delivery_date:%d%m%y}' or ('0' * 6))
                + (' ' * 72)
        )


@define
class SectionStartRecord(Record):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    data_supplier_id: str = field(converter=to_safe_str_or_none)
    section_type: 'SectionType' = field(converter=to_section_type)
    section_date: Union['datetime.date', None] = field(converter=to_date_or_none)
    main_text_line: Optional[str] = field(default=None, converter=to_safe_str_or_none)

    RECORD_TYPE = RecordType.SECTION_START
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            012 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<section_type>0112) # Section Number
            [ ]{5}
            (?P<debtor_group_number>\d{5})
            (?P<data_supplier_id>.{15})
            [ ]{4}
            (?P<section_date>\d{8})
            [ ]{0,14}
            (?P<main_text_line>.{60})
            $ 
            ''',
            re.VERBOSE,
        ), re.compile(
            r'''
            ^
            BS
            012 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<section_type>\d{4}) # Section Number
            .{3}
            (?P<debtor_group_number>\d{5})
            (?P<data_supplier_id>.{15})
            [ ]{9}
            (?P<section_date>\d{6})
            [ ]{73}
            $ 
            ''',
            re.VERBOSE,
        ),
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        common_fields = (
                f'BS012'
                + f'{self.pbs_number:08d}'
                + f'{self.section_type:04d}'
        )
        if self.section_type == SectionType.COLLECTION:
            section_fields = (
                    ' ' * 5
                    + f'{self.debtor_group_number:05d}'
                    + (self.data_supplier_id and f'{self.data_supplier_id:15}' or (' ' * 15))
                    + (' ' * 4)
                    + (self.section_date and f'{self.section_date:%d%m%Y}' or ('0' * 8))
                    + (' ' * 14)
                    + (self.main_text_line and f'{self.main_text_line:60}' or (' ' * 60))
            )
        else:
            section_fields = (
                    (' ' if self.section_type == SectionType.REGISTERED_AND_CANCELLED_MANDATE else '0') * 3
                    + f'{self.debtor_group_number:05d}'
                    + (self.data_supplier_id and f'{self.data_supplier_id:15}' or (' ' * 15))
                    + (' ' * 9)
                    + (self.section_date and f'{self.section_date:%d%m%y}' or ('0' * 6))
                    + (' ' * 73)
            )
        return common_fields + section_fields


@define
class InfoRecord(Record):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    customer_number: str = field(validator=str_of_length(15))
    mandate_number: int = field(converter=int)
    info_date: 'datetime.date' = field(converter=to_date_or_none)
    transaction_code: TransactionCode = field(converter=to_transaction_code)

    # 0603 Mandate Specific
    end_date: Optional['datetime.date'] = field(default=None, converter=to_date_or_none)

    # 0602 Payment Specific
    payment_date: Optional['datetime.date'] = field(default=None, converter=to_date_or_none)
    bookkeping_date: Optional['datetime.date'] = field(default=None, converter=to_date_or_none)
    payment_amount: Optional[int] = field(default=None, converter=to_int_or_none)

    # 0601 Collection Specific
    payer_id: Optional[int] = field(default=None, converter=to_int_or_none)

    # 0601 and 0602
    sign_code: Optional['SignCode'] = field(default=None, converter=to_sign_code)
    amount: Optional[int] = field(default=None, converter=to_int_or_none)
    reference: Optional[str] = field(default=None, converter=to_safe_str_or_none)

    RECORD_TYPE = RecordType.INFO
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            042 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<transaction_code>0280)
            00000
            (?P<debtor_group_number>\d{5})
            (?P<customer_number>.{15})
            (?P<mandate_number>\d{9})
            (?P<info_date>\d{8})
            (?P<sign_code>\d{1})
            (?P<amount>\d{13})
            (?P<reference>.{30})
            00
            (?P<payer_id>.{15})
            0{8}
            $ 
            ''',
            re.VERBOSE,
        ), re.compile(
            r'''
            ^
            BS
            042 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<transaction_code>\d{4})
            000
            (?P<debtor_group_number>\d{5})
            (?P<customer_number>.{15})
            (?P<mandate_number>\d{9})
            (?P<info_date>\d{6})
            (?P<end_date>\d{6})
            [ ]{67}
            $ 
            ''',
            re.VERBOSE,
        ),
        re.compile(
            r'''
            ^
            BS
            042 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<transaction_code>\d{4})
            000
            (?P<debtor_group_number>\d{5})
            (?P<customer_number>.{15})
            (?P<mandate_number>\d{9})
            (?P<info_date>\d{6})
            (?P<sign_code>\d{1})
            (?P<amount>\d{13})
            (?P<reference>.{30})
            [ ]{4}
            (?P<payment_date>\d{6})
            (?P<bookkeping_date>\d{6})
            (?P<payment_amount>\d{13})
            $ 
            ''',
            re.VERBOSE,
        )
    ]

    def to_ocr(self) -> str:
        """Get record as OCR string."""
        common_part = (f'BS042'
                       + f'{self.pbs_number:08d}'
                       + f'{self.transaction_code:04d}')
        if self.transaction_code == TransactionCode.COLLECTION_INFORMATION:
            transaction_spec = (
                    f'00000'
                    + f'{self.debtor_group_number:05d}'
                    + f'{self.customer_number:15}'
                    + f'{self.mandate_number:09d}'
                    + f'{self.info_date:%d%m%Y}'
                    + f'{self.sign_code:01d}'
                    + f'{self.amount:013d}'
                    + (self.reference and f'{self.reference:30}' or (' ' * 30))
                    + '00'
                    + (self.payer_id and f'{self.payer_id:15}' or (' ' * 15))
                    + ('0' * 8))

        elif self.transaction_code == TransactionCode.MANDATE_REGISTERED:
            transaction_spec = (
                    f'000'
                    + f'{self.debtor_group_number:05d}'
                    + f'{self.customer_number:15}'
                    + f'{self.mandate_number:09d}'
                    + f'{self.info_date:%d%m%y}'
                    + (self.end_date and f'{self.end_date:%y%m%d}' or ('0' * 6))
                    + (' ' * 67)
            )
        else:
            transaction_spec = (
                    f'000'
                    + f'{self.debtor_group_number:05d}'
                    + f'{self.customer_number:15}'
                    + f'{self.mandate_number:09d}'
                    + f'{self.info_date:%d%m%y}'
                    + f'{self.sign_code:01d}'
                    + f'{self.amount:013d}'
                    + (self.reference and f'{self.reference:30}' or (' ' * 30))
                    + (' ' * 4)
                    + (self.payment_date and f'{self.payment_date:%d%m%y}' or ('0' * 6))
                    + (self.bookkeping_date and f'{self.bookkeping_date:%d%m%y}' or ('0' * 6))
                    + f'{self.payment_amount:013d}'
            )
        return common_part + transaction_spec


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
    section_type: 'SectionType' = field(converter=to_section_type)
    RECORD_TYPE: ClassVar[RecordType] = RecordType.SECTION_END
    _PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r'''
            ^
            BS
            092 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<section_type>0112) # Section Number
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
        ), re.compile(
            r'''
            ^
            BS
            092 # Data Record Type
            (?P<pbs_number>\d{8})
            (?P<section_type>\d{4}) # Section Number
            000
            (?P<debtor_group_number>\d{5})
            [ ]{6}
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
        common_part = (
                f'BS092'
                + f'{self.pbs_number:08d}'
                + f'{self.section_type:04d}')
        if self.section_type == SectionType.COLLECTION:
            section_spec = (f'00000'
                            + f'{self.debtor_group_number:05d}'
                            + (' ' * 4)
                            + f'{self.num_of_record_42:011d}'
                            + f'{self.net_amount:015d}'
                            + f'{self.num_of_record_52_62:011d}'
                            + (' ' * 15)
                            + f'{self.num_of_record_22:011d}'
                            + (' ' * 34)
                            )
        else:
            section_spec = (f'000'
                            + f'{self.debtor_group_number:05d}'
                            + (' ' * 6)
                            + f'{self.num_of_record_42:011d}'
                            + f'{self.net_amount:015d}'
                            + f'{self.num_of_record_52_62:011d}'
                            + (' ' * 15)
                            + f'{self.num_of_record_22:011d}'
                            + (' ' * 34)
                            )
        return common_part + section_spec


@define
class DataDeliveryEndRecord(Record):
    data_supplier_number: int = field(converter=int)
    subsystem: str = field(validator=str_of_length(3))
    delivery_type: 'DeliveryType' = field(converter=to_delivery_type)
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
            (?P<delivery_type>\d{4})# Data Delivery Type
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
                + f'{self.delivery_type:04d}'
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
