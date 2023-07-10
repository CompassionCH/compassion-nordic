##############################################################################
#
#    Copyright (C) 2015-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#
#    The licence is in the file __manifest__.py
#
##############################################################################
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
        for payment in self.payment_ids:
            payment_initiation.add_payment(
                transaction_type=bggiro.TransactionType.INCOMING_PAYMENT,
                payment_date=payment.date,
                period_code=bggiro.PeriodCode.ONCE,
                number_recurring_payments=0,
                payer_number=int(payment.move_id.line_ids.mapped('contract_id').group_id.ref),
                amount=int(payment.amount),
                reference=payment.id[:16])
        return payment_initiation.to_ocr().encode('iso-8859-1'), "{}.txt".format(self.name)
