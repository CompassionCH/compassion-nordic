"""The higher-level objects API."""

import datetime
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING, Iterable, List, Tuple
from typing import OrderedDict as OrderedDictType
from attrs import Factory, define, field
from .converters import *
from .enums import SignCode, SectionType, TransactionCode, DeliveryType
from .records import (
    Record,
    DataDeliveryStartRecord,
    DataDeliveryEndRecord,
    SectionStartRecord,
    SectionEndRecord,
    InfoRecord,
    TextToDebtorRecord

)
from .records import parse as records_parse
from .validators import str_of_length

if TYPE_CHECKING:
    from records import Record

__all__: List[str] = [
    'DataDeliveryCollection',
    'Collection',
    'parse',
    'PaymentInformation'
]

# Record or Record subclasses
R = TypeVar('R', bound='Record')


@define
class DataDelivery(ABC):
    data_supplier_number: int = field(converter=int)
    subsystem: str = field(validator=str_of_length(3))
    delivery_type: 'DeliveryType' = field(converter=to_delivery_type)
    delivery_identification: int = field(converter=int)
    delivery_date: Optional[datetime.date] = field(default=None, converter=to_date_or_none)
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
            delivery_date=start.delivery_date,
            delivery_type=start.delivery_type,
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
            delivery_date=self.delivery_date,
            delivery_type=self.delivery_type
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
            delivery_type=self.delivery_type
        )


@define
class DataDeliveryCollection(DataDelivery):
    def add_section(self, pbs_number: int, debtor_group_number: int, data_supplier_id: str,
                    main_text_line: Optional[str] = None) -> 'CollectionSection':
        section = CollectionSection(pbs_number=pbs_number,
                                    debtor_group_number=debtor_group_number,
                                    data_supplier_id=data_supplier_id,
                                    main_text_line=main_text_line,
                                    section_type=SectionType.COLLECTION,
                                    section_date=self.delivery_date)
        self.sections.append(section)
        return section


@define
class Section(ABC):
    section_type: SectionType = field(converter=to_section_type)
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    data_supplier_id: str = field(converter=to_safe_str_or_none)
    main_text_line: str = field(converter=to_safe_str_or_none)
    section_date: Union[datetime.date, None] = field(converter=to_date_or_none)
    information_list: List['InformationData'] = field(default=Factory(list), repr=False)

    @classmethod
    def from_records(cls, records: List[R]):
        start = records[0]
        assert isinstance(start, SectionStartRecord)
        if start.section_type == SectionType.COLLECTION:
            return CollectionSection.from_records(records)
        elif start.section_type == SectionType.REGISTERED_AND_CANCELLED_MANDATE:
            return MandateModificationSection.from_records(records)
        elif start.section_type == SectionType.AUTOMATED_PAYMENT_INFORMATION:
            return PaymentInformationSection.from_records(records)

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield self._get_start_record()
        for information in self.information_list:
            yield from information.to_records()
        yield self._get_end_record()

    def _get_start_record(self):
        return SectionStartRecord(pbs_number=self.pbs_number,
                                  debtor_group_number=self.debtor_group_number,
                                  data_supplier_id=self.data_supplier_id,
                                  section_date=self.section_date,
                                  section_type=self.section_type,
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
        payment = Collection(pbs_number=self.pbs_number,
                             debtor_group_number=self.debtor_group_number,
                             customer_number=customer_number,
                             mandate_number=mandate_number,
                             info_date=payment_date,
                             sign_code=sign_code,
                             amount=amount,
                             reference=reference,
                             payer_id=payer_id,
                             text_lines=self._parse_text_line(text_lines),
                             transaction_code=TransactionCode.COLLECTION_INFORMATION)
        self.information_list.append(payment)
        return payment

    def get_num_of_record_42(self):
        return len(self.information_list)

    def get_num_of_record_52_62(self):
        return sum([information.get_num_of_record_52_62() for information in self.information_list])

    @abstractmethod
    def get_net_amount(self):
        pass

    @staticmethod
    def get_num_of_record_22():
        return 0

    def _get_end_record(self):
        return SectionEndRecord(pbs_number=self.pbs_number,
                                section_type=self.section_type,
                                debtor_group_number=self.debtor_group_number,
                                num_of_record_42=self.get_num_of_record_42(),
                                net_amount=self.get_net_amount(),
                                num_of_record_52_62=self.get_num_of_record_52_62(),
                                num_of_record_22=self.get_num_of_record_22()
                                )


class CollectionSection(Section):

    def get_net_amount(self):
        sum_amount = 0
        for record in self.information_list:
            assert (isinstance(record, Collection))
            sum_amount += record.amount
        return sum_amount

    @staticmethod
    def _get_payments(records: List[R]) -> List['Collection']:
        payments = []
        temp_payment_records = []
        for record in records:
            if isinstance(record, InfoRecord) and temp_payment_records:
                payments.append(temp_payment_records)
                temp_payment_records = []
            elif isinstance(record, TextToDebtorRecord) and not temp_payment_records:
                raise ValueError(f'Expected PaymentInfoRecord record, got {record!r}')
            temp_payment_records.append(record)
        if temp_payment_records:
            payments.append(temp_payment_records)
        return [Collection.from_records(payment) for payment in payments]

    @classmethod
    def from_records(cls, records: List[R]) -> 'CollectionSection':
        """Build a Section object from a list of record objects."""
        start, body, end = records[0], records[1:-1], records[-1]
        assert isinstance(start, SectionStartRecord)
        assert isinstance(end, SectionEndRecord)
        return cls(
            pbs_number=start.pbs_number,
            debtor_group_number=start.debtor_group_number,
            data_supplier_id=start.data_supplier_id,
            main_text_line=start.main_text_line,
            section_date=start.section_date,
            section_type=start.section_type,
            information_list=cls._get_payments(body)
        )


@define
class MandateModificationSection(Section):

    def get_net_amount(self):
        return 0

    @staticmethod
    def _get_mandate(records: List[R]) -> List['MandateRegistration']:
        for record in records:
            assert (isinstance(record, InfoRecord))
        return [MandateRegistration.from_records([record]) for record in records]

    @classmethod
    def from_records(cls, records: List[R]) -> 'MandateModificationSection':
        """Build a Section object from a list of record objects."""
        start, body, end = records[0], records[1:-1], records[-1]
        assert isinstance(start, SectionStartRecord)
        assert isinstance(end, SectionEndRecord)
        return cls(
            pbs_number=start.pbs_number,
            debtor_group_number=start.debtor_group_number,
            data_supplier_id=start.data_supplier_id,
            main_text_line=start.main_text_line,
            section_date=start.section_date,
            section_type=start.section_type,
            information_list=cls._get_mandate(body)
        )


@define
class PaymentInformationSection(Section):
    @classmethod
    def from_records(cls, records: List[R]):
        start, body, end = records[0], records[1:-1], records[-1]
        assert isinstance(start, SectionStartRecord)
        assert isinstance(end, SectionEndRecord)
        return cls(
            pbs_number=start.pbs_number,
            debtor_group_number=start.debtor_group_number,
            data_supplier_id=start.data_supplier_id,
            main_text_line=start.main_text_line,
            section_date=start.section_date,
            section_type=start.section_type,
            information_list=cls._get_payment_information(body)
        )

    def get_net_amount(self):
        sum_amount = 0
        for record in self.information_list:
            assert (isinstance(record, PaymentInformation))
            sum_amount += record.amount
        return sum_amount

    @staticmethod
    def _get_payment_information(body):
        return [PaymentInformation.from_records([record]) for record in body]


@define
class InformationData(ABC):
    pbs_number: int = field(converter=int)
    debtor_group_number: int = field(converter=int)
    customer_number: str = field(validator=str_of_length(15))
    mandate_number: int = field(converter=int)
    transaction_code: TransactionCode = field(converter=to_transaction_code)
    info_date: 'datetime.date' = field(converter=to_date_or_none)

    @classmethod
    @abstractmethod
    def from_records(cls, records: List[R]):
        pass

    @abstractmethod
    def to_records(self) -> Iterable['Record']:
        pass

    @abstractmethod
    def get_num_of_record_52_62(self):
        pass


@define
class Collection(InformationData):
    sign_code: 'SignCode' = field(converter=to_sign_code)
    amount: int = field(converter=int)
    reference: str = field(converter=to_safe_str_or_none)
    payer_id: int = field(converter=to_int_or_none)
    text_lines: OrderedDictType[int, List[str]] = field(default=Factory(OrderedDictType), repr=False)

    @classmethod
    def from_records(cls, records: List[R]) -> 'Collection':
        """Build an Section object from a list of record objects."""
        info, text_lines_rec = records[0], records[1:]
        assert isinstance(info, InfoRecord)
        return cls(
            sign_code=info.sign_code,
            amount=int(info.amount / 100),
            reference=info.reference,
            payer_id=info.payer_id,
            text_lines=cls._get_text_lines(text_lines_rec),
            pbs_number=info.pbs_number,
            debtor_group_number=info.debtor_group_number,
            customer_number=info.customer_number,
            mandate_number=info.mandate_number,
            transaction_code=info.transaction_code,
            info_date=info.info_date
        )

    @staticmethod
    def get_net_amount():
        return 0

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
        return InfoRecord(
            pbs_number=self.pbs_number,
            debtor_group_number=self.debtor_group_number,
            customer_number=self.customer_number,
            mandate_number=self.mandate_number,
            info_date=self.info_date,
            sign_code=self.sign_code,
            amount=self.amount * 100,
            reference=self.reference,
            payer_id=self.payer_id,
            transaction_code=self.transaction_code)

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


@define
class MandateRegistration(InformationData):
    start_date: 'datetime.date' = field(converter=to_date_or_none)
    end_date: 'datetime.date' = field(converter=to_date_or_none)

    def get_num_of_record_52_62(self):
        return 0

    @classmethod
    def from_records(cls, records: List[R]) -> 'MandateRegistration':
        """Build an Section object from a list of record objects."""
        record = records[0]
        assert isinstance(record, InfoRecord)
        return cls(
            pbs_number=record.pbs_number,
            debtor_group_number=record.debtor_group_number,
            customer_number=record.customer_number,
            mandate_number=record.mandate_number,
            start_date=record.info_date,
            end_date=record.end_date,
            transaction_code=record.transaction_code,
            info_date=record.info_date
        )

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield InfoRecord(
            pbs_number=self.pbs_number,
            debtor_group_number=self.debtor_group_number,
            customer_number=self.customer_number,
            mandate_number=self.mandate_number,
            info_date=self.start_date,
            end_date=self.end_date,
            transaction_code=self.transaction_code
        )


@define
class PaymentInformation(InformationData):
    sign_code: 'SignCode' = field(converter=to_sign_code)
    amount: int = field(converter=to_int_or_none)
    reference: Optional[str] = field(default=None, converter=to_safe_str_or_none)
    payment_date: Optional['datetime.date'] = field(default=None, converter=to_date_or_none)
    bookkeping_date: Optional['datetime.date'] = field(default=None, converter=to_date_or_none)
    payment_amount: Optional[int] = field(default=None, converter=to_int_or_none)

    def get_num_of_record_52_62(self):
        return 0

    @classmethod
    def from_records(cls, records: List[R]) -> 'PaymentInformation':
        """Build an Section object from a list of record objects."""
        record = records[0]
        assert isinstance(record, InfoRecord)
        return cls(
            pbs_number=record.pbs_number,
            debtor_group_number=record.debtor_group_number,
            customer_number=record.customer_number,
            mandate_number=record.mandate_number,
            transaction_code=record.transaction_code,
            payment_date=record.payment_date,
            bookkeping_date=record.bookkeping_date,
            payment_amount=int(record.payment_amount / 100) if record.payment_amount is not None else None,
            info_date=record.info_date,
            amount=int(record.amount / 100) if record.amount is not None else None,
            sign_code=record.sign_code,
            reference=record.reference
        )

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield InfoRecord(
            pbs_number=self.pbs_number,
            debtor_group_number=self.debtor_group_number,
            customer_number=self.customer_number,
            mandate_number=self.mandate_number,
            transaction_code=self.transaction_code,
            info_date=self.info_date,
            payment_date=self.payment_date,
            bookkeping_date=self.bookkeping_date,
            payment_amount=self.payment_amount * 100 if self.payment_amount is not None else None,
            amount=self.amount * 100 if self.amount is not None else None,
            sign_code=self.sign_code,
            reference=self.reference
        )


def parse(data: str) -> DataDelivery:
    """Parse an OCR file into a Transmission object."""
    return DataDelivery.from_records(records_parse(data))
