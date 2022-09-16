"""The higher-level objects API."""

import datetime
from decimal import Decimal
from collections import OrderedDict
from typing import TYPE_CHECKING, Iterable, List, Tuple, Optional
from typing import TypeVar, Union
from typing import OrderedDict as OrderedDictType
from attrs import Factory, define, field
from attrs.validators import instance_of
import netsgiro
from .converters import (
    to_date_short_or_none, to_safe_str_or_none, to_date, to_sign_code, to_int_or_none, to_date_long_or_none,

)
from .enums import SignCode, RecordType
from .records import (
    DataDeliveryStartRecord,
    DataDeliveryEndRecord,
    SectionStartRecord,
    SectionEndRecord,
    PaymentInfoRecord,
    TextToDebtorRecord

)
from .records import parse as records_parse
from .validators import str_of_length

if TYPE_CHECKING:
    from records import Record

__all__: List[str] = [
    'DataDelivery',
    'Payment',
    'parse',
]

# Record or Record subclasses
R = TypeVar('R', bound='Record')


@define
class DataDelivery:
    data_supplier_number: int = field(converter=int)
    subsystem: str = field(validator=str_of_length(3))
    delivery_identification: int = field(converter=int)
    date: Optional[datetime.date] = field(default=None, converter=to_date_short_or_none)
    sections: List['Section'] = field(default=Factory(list), repr=False)

    @classmethod
    def from_records(cls, records: List[R]) -> 'DataDelivery':
        """Build a Transmission object from a list of record objects."""
        if len(records) < 1:
            raise ValueError(f'At least 2 records required, got {len(records)}')

        start, body, end = records[0], records[1:-1], records[-1]
        assert isinstance(start, DataDeliveryStartRecord)
        assert isinstance(end, DataDeliveryEndRecord)
        return cls(
            data_supplier_number=start.data_supplier_number,
            subsystem=start.subsystem,
            delivery_identification=start.delivery_identification,
            date=start.date,
            sections=cls._get_sections(body),
        )

    @staticmethod
    def _get_sections(records: List[R]) -> List['Section']:
        section_records = []
        temp_section_record = []
        for record in records:
            if isinstance(record, SectionStartRecord):
                if temp_section_record:
                    raise ValueError(f'Expected Section End record, got {record!r}')
                temp_section_record.append(record)
            elif isinstance(record, SectionEndRecord):
                if not temp_section_record:
                    raise ValueError(f'Expected Section Start record, got {record!r}')
                temp_section_record.append(record)
                section_records.append(temp_section_record)
                temp_section_record = []
            else:
                if not temp_section_record:
                    raise ValueError(f'Expected Section Start record, got {record!r}')
                temp_section_record.append(record)
        if temp_section_record:
            raise ValueError(f'Expected Section End record at the end')

        return [Section.from_records(rs) for rs in section_records]

    def to_ocr(self) -> str:
        """Convert the transmission to an OCR string."""
        lines = [record.to_ocr() for record in self.to_records()]
        return '\n'.join(lines)

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield self._get_start_record()
        for section in self.sections:
            yield from section.to_records()
        yield self._get_end_record()

    def _get_start_record(self) -> 'Record':
        return DataDeliveryStartRecord(
            data_supplier_number=self.data_supplier_number,
            subsystem=self.subsystem,
            delivery_identification=self.delivery_identification,
            date=self.date,
        )

    def get_num_of_record_42(self):
        return sum([section.get_num_of_record_42() for section in self.sections])

    def get_num_of_record_52_62(self):
        return sum([section.get_num_of_record_52_62() for section in self.sections])

    def get_num_of_record_22(self):
        return sum([section.get_num_of_record_22() for section in self.sections])

    def get_net_amount(self):
        return sum([section.get_net_amount() for section in self.sections])

    def _get_end_record(self) -> 'Record':
        return DataDeliveryEndRecord(
            data_supplier_number=self.data_supplier_number,
            subsystem=self.subsystem,
            num_of_section=len(self.sections),
            num_of_record_42=self.get_num_of_record_42(),
            net_amount=self.get_net_amount(),
            num_of_record_52_62=self.get_num_of_record_52_62(),
            num_of_record_22=self.get_num_of_record_22(),
        )

    def add_section(self, pbs_number: int, debtor_group_number: int, data_supplier_id: str,
                    main_text_line: Optional[str] = None) -> 'Section':
        section = Section(pbs_number=pbs_number,
                          debtor_group_number=debtor_group_number,
                          data_supplier_id=data_supplier_id,
                          main_text_line=main_text_line,
                          date=self.date)
        self.sections.append(section)
        return section


@define
class Section:
    # 82 = Incoming payment (withdrawal from the payer's bank account or bankgiro number)
    # 32 = Outgoing payment(deposit in the payer's bank account or bankgiro number)
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    data_supplier_id: str = field(converter=to_safe_str_or_none)
    main_text_line: str = field(converter=to_safe_str_or_none)
    date: Union[datetime.date, None] = field(converter=to_date_long_or_none)
    payments: List['Payment'] = field(default=Factory(list), repr=False)

    @classmethod
    def from_records(cls, records: List[R]) -> 'Section':
        """Build a Section object from a list of record objects."""
        start, body, end = records[0], records[1:-1], records[-1]
        assert isinstance(start, SectionStartRecord)
        assert isinstance(end, SectionEndRecord)

        return cls(
            pbs_number=start.pbs_number,
            debtor_group_number=start.debtor_group_number,
            data_supplier_id=start.data_supplier_id,
            main_text_line=start.main_text_line,
            date=start.date,
            payments=cls._get_payments(body)
        )

    @staticmethod
    def _get_payments(records: List[R]) -> List['Payment']:
        payments = []
        temp_payment_records = []
        for record in records:
            if isinstance(record, PaymentInfoRecord) and temp_payment_records:
                payments.append(temp_payment_records)
                temp_payment_records = []
            elif isinstance(record, TextToDebtorRecord) and not temp_payment_records:
                raise ValueError(f'Expected PaymentInfoRecord record, got {record!r}')
            temp_payment_records.append(record)
        if temp_payment_records:
            payments.append(temp_payment_records)
        return [Payment.from_records(payment) for payment in payments]

    def _get_start_record(self):
        return SectionStartRecord(pbs_number=self.pbs_number,
                                  debtor_group_number=self.debtor_group_number,
                                  data_supplier_id=self.data_supplier_id,
                                  date=self.date,
                                  main_text_line=self.main_text_line)

    @staticmethod
    def _parse_text_line(text_lines: List[Tuple[int, str]]) -> OrderedDictType[int, List[str]]:
        parsed_text_lines: OrderedDictType[int, List[str]] = OrderedDict()
        for text_line in text_lines:
            rec_num = text_line[0]
            if rec_num not in parsed_text_lines:
                parsed_text_lines[rec_num] = []
            parsed_text_lines[rec_num].append(text_line[1])
        return parsed_text_lines

    def add_payment(self, customer_number: str, mandate_number: int, payment_date: datetime.date, sign_code: 'SignCode',
                    amount: int, reference: Optional[str] = None, payer_id: Optional[int] = None,
                    text_lines=None):
        if text_lines is None:
            text_lines = []
        payment = Payment(pbs_number=self.pbs_number,
                          debtor_group_number=self.debtor_group_number,
                          customer_number=customer_number,
                          mandate_number=mandate_number,
                          payment_date=payment_date,
                          sign_code=sign_code,
                          amount=amount,
                          reference=reference,
                          payer_id=payer_id,
                          text_lines=self._parse_text_line(text_lines))
        self.payments.append(payment)
        return payment

    def get_num_of_record_42(self):
        return len(self.payments)

    def get_num_of_record_52_62(self):
        return sum([payment.get_num_of_record_52_62() for payment in self.payments])

    @staticmethod
    def get_num_of_record_22():
        return 0

    def get_net_amount(self):
        return sum([payment.amount for payment in self.payments])

    def _get_end_record(self):
        return SectionEndRecord(pbs_number=self.pbs_number,
                                debtor_group_number=self.debtor_group_number,
                                num_of_record_42=self.get_num_of_record_42(),
                                net_amount=self.get_net_amount(),
                                num_of_record_52_62=self.get_num_of_record_52_62(),
                                num_of_record_22=self.get_num_of_record_22()
                                )

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield self._get_start_record()
        for payment in self.payments:
            yield from payment.to_records()
        yield self._get_end_record()


@define
class Payment:
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    customer_number: str = field(validator=str_of_length(15))
    mandate_number: int = field(converter=int)
    payment_date: datetime.date = field(converter=to_date)
    sign_code: 'SignCode' = field(converter=to_sign_code)
    amount: int = field(converter=int)
    reference: str = field(converter=to_safe_str_or_none)
    payer_id: int = field(converter=to_int_or_none)
    text_lines: OrderedDictType[int, List[str]] = field(default=Factory(OrderedDictType), repr=False)

    @classmethod
    def from_records(cls, records: List[R]) -> 'Payment':
        """Build an Section object from a list of record objects."""
        info, text_lines_rec = records[0], records[1:]
        assert isinstance(info, PaymentInfoRecord)

        return cls(
            pbs_number=info.pbs_number,
            debtor_group_number=info.debtor_group_number,
            customer_number=info.customer_number,
            mandate_number=info.mandate_number,
            payment_date=info.payment_date,
            sign_code=info.sign_code,
            amount=info.amount,
            reference=info.reference,
            payer_id=info.payer_id,
            text_lines=cls._get_text_lines(text_lines_rec)
        )

    @staticmethod
    def _get_text_lines(records: List[R]) -> OrderedDictType[int, List[str]]:
        text_lines: OrderedDictType[int, List[str]] = OrderedDict()
        for record in records:
            assert (isinstance(record, TextToDebtorRecord))
            rec_num = record.data_record_num
            if rec_num not in text_lines:
                text_lines[rec_num] = []
            text_lines[rec_num].append(record.text_line)
        return text_lines

    def get_num_of_record_52_62(self):
        return sum([len(val) for val in self.text_lines.values()])

    def _get_payment_info(self):
        return PaymentInfoRecord(
            pbs_number=self.pbs_number,
            debtor_group_number=self.debtor_group_number,
            customer_number=self.customer_number,
            mandate_number=self.mandate_number,
            payment_date=self.payment_date,
            sign_code=self.sign_code,
            amount=self.amount,
            reference=self.reference,
            payer_id=self.payer_id)

    def _text_line_to_record(self, text_line, data_record_num):
        return TextToDebtorRecord(
            pbs_number=self.pbs_number,
            data_record_num=data_record_num,
            debtor_group_number=self.debtor_group_number,
            customer_number=self.customer_number,
            mandate_number=self.mandate_number,
            text_line=text_line)

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield self._get_payment_info()
        for val in self.text_lines.items():
            for line in val[1]:
                yield self._text_line_to_record(line, val[0])


def parse(data: str) -> DataDelivery:
    """Parse an OCR file into a Transmission object."""
    return DataDelivery.from_records(records_parse(data))
