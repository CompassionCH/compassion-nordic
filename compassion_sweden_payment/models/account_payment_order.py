# Copyright 2020 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models
from .. import bggiro


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def format_transmission_number(self):
        return "{}1".format(self.create_date.strftime("%d%m%y"))

    def generate_payment_file(self):
        self.ensure_one()
        if self.payment_method_id.code != "sweden_direct_debit":
            return super().generate_payment_file()
        payment_initiation = bggiro.PaymentInitiation(date_written=self.create_date,
                                                      bankgiro_number=self.company_partner_bank_id.acc_number,
                                                      customer_number=self.payment_mode_id.initiating_party_identifier)
        for payment_line in self.payment_line_ids:
            payment_initiation.add_payment(
                transaction_type=bggiro.TransactionType.INCOMING_PAYMENT,
                payment_date=payment_line.date,
                period_code=bggiro.PeriodCode.ONCE,
                number_recurring_payments=0,
                payer_number=int(payment_line.move_line_id.move_id.line_ids.mapped('contract_id').group_id.ref),
                amount=int(payment_line.amount_currency),
                reference=payment_line.communication)
        return payment_initiation.to_ocr().encode('iso-8859-1'), "{}.xml".format(self.name)
