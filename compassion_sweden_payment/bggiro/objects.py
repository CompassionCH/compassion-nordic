"""The higher-level objects API."""

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable, List
from typing import TypeVar, Union

from attrs import Factory, define, field
from attrs.validators import instance_of

from .converters import (
    to_transaction_type, to_date_or_genast, to_period_code, to_safe_str_or_none,
    number_recurring_payments_to_int
)
from .enums import TransactionType, PeriodCode
from .records import (
    OpeningRecord,
    PaymentRecord
)
from .records import parse as records_parse
from .validators import str_of_length

if TYPE_CHECKING:
    from records import Record

__all__: List[str] = [
    'PaymentInitiation',
    'Payment',
    'parse',
]

# Record or Record subclasses
R = TypeVar('R', bound='Record')


@define
class PaymentInitiation:
    """Transmission is the top-level object.

    An OCR file contains a single transmission. The transmission can contain
    multiple :class:`~netsgiro.Assignment` objects of various types.
    """
    #: The date the file was created at the payee.
    date_written: datetime.date = field(
        validator=instance_of(datetime.date)
    )

    # Payee's customer number at Bankgirot. String of 6 digits.
    customer_number: str = field(validator=str_of_length(6))

    #: Payee's bankgiro number. String of 10 digits.
    bankgiro_number: str = field(validator=str_of_length(10))

    #: List of Payment.
    payments: List['Payment'] = field(default=Factory(list), repr=False)

    @classmethod
    def from_records(cls, records: List[R]) -> 'PaymentInitiation':
        """Build a Transmission object from a list of record objects."""
        if len(records) < 1:
            raise ValueError(f'At least 2 records required, got {len(records)}')

        opening_record, body = records[0], records[1:]

        assert isinstance(opening_record, OpeningRecord)

        return cls(
            date_written=opening_record.date_written,
            customer_number=opening_record.customer_number,
            bankgiro_number=opening_record.payer_bankgiro_number,
            payments=cls._get_incoming_payment(body),
        )

    @staticmethod
    def _get_incoming_payment(records: List[R]) -> List['Payment']:
        payment_records = []
        for record in records:
            if isinstance(record, PaymentRecord):
                payment_records.append(record)
            else:
                raise ValueError(f'Record is not an Instance of Payment Record')

        return [Payment.from_records(rs) for rs in payment_records]

    def to_ocr(self) -> str:
        """Convert the transmission to an OCR string."""
        lines = [record.to_ocr() for record in self.to_records()]
        return '\n'.join(lines)

    def to_records(self) -> Iterable['Record']:
        """Convert the transmission to a list of records."""
        yield self._get_opening_record()
        for payment in self.payments:
            yield payment.to_record()

    def _get_opening_record(self) -> 'Record':
        return OpeningRecord(
            customer_number=self.customer_number,
            payer_bankgiro_number=self.bankgiro_number,
            date_written=self.date_written
        )

    def add_payment(
            self,
            transaction_type: TransactionType,
            payment_date: Union[datetime.date, str],
            period_code: PeriodCode,
            number_recurring_payments: int,
            payer_number: int,
            amount: Decimal,
            reference: str,
    ) -> 'Payment':

        payment = Payment(
            transaction_type=transaction_type,
            payment_date=payment_date,
            period_code=period_code,
            number_recurring_payments=number_recurring_payments,
            payer_number=payer_number,
            payee_bankgiro_number=self.bankgiro_number,
            amount=amount,
            reference=reference
        )

        self.payments.append(payment)
        return payment

    def get_num_transactions(self) -> int:
        """Get number of transactions in the transmission."""
        return sum(assignment.get_num_transactions() for assignment in self.assignments)

    def get_num_records(self) -> int:
        """Get number of records in the transmission.

        Includes the transmission's start and end record.
        """
        return 2 + sum(assignment.get_num_records() for assignment in self.assignments)

    def get_total_amount(self) -> Decimal:
        """Get the total amount from all transactions in the transmission."""
        return Decimal(sum(assignment.get_total_amount() for assignment in self.assignments))


@define
class Payment:
    # 82 = Incoming payment (withdrawal from the payer's bank account or bankgiro number)
    # 32 = Outgoing payment(deposit in the payer's bank account or bankgiro number)
    transaction_type: 'TransactionType' = field(converter=to_transaction_type)

    payment_date: Union[datetime.date, str] = field(converter=to_date_or_genast)

    period_code: 'PeriodCode' = field(converter=to_period_code)

    number_recurring_payments: int = field(converter=number_recurring_payments_to_int)

    payer_number: int = field(converter=int)

    payee_bankgiro_number: int = field(converter=int)

    amount: int = field(converter=int)

    reference: str = field(converter=to_safe_str_or_none)

    @property
    def amount_in_cents(self) -> int:
        """Transaction amount in NOK cents."""
        return int(self.amount * 100)

    @classmethod
    def from_records(cls, record: PaymentRecord) -> 'Payment':
        """Build an Assignment object from a list of record objects."""

        assert isinstance(record, PaymentRecord)

        return cls(
            transaction_type=record.transaction_type,
            payment_date=record.payment_date,
            period_code=record.period_code,
            number_recurring_payments=record.number_recurring_payments,
            payer_number=record.payer_number,
            payee_bankgiro_number=record.payee_bankgiro_number,
            amount=Decimal(record.amount) / 100,
            reference=record.reference
        )

    def to_record(self) -> 'Record':
        """Convert the transmission to a list of records."""
        return PaymentRecord(transaction_type=self.transaction_type,
                             payment_date=self.payment_date,
                             period_code=self.period_code,
                             number_recurring_payments=self.number_recurring_payments,
                             payer_number=self.payer_number,
                             payee_bankgiro_number=self.payee_bankgiro_number,
                             amount=self.amount_in_cents,
                             reference=self.reference)


def parse(data: str) -> PaymentInitiation:
    """Parse an OCR file into a Transmission object."""
    return PaymentInitiation.from_records(records_parse(data))
