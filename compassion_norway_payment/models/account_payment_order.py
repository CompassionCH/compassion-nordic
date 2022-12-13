##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################


from lxml import etree

from odoo import models
import netsgiro


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def format_transmission_number(self):
        return "{}1".format(self.date_generated.strftime("%d%m%y"))

    def generate_payment_file(self):
        self.ensure_one()
        if self.payment_method_id.code != "norway_direct_debit":
            return super().generate_payment_file()
        transmission = netsgiro.Transmission(
            number=self.format_transmission_number(),
            data_transmitter=self.payment_mode_id.initiating_party_identifier,
            data_recipient=netsgiro.NETS_ID)

        assignment = transmission.add_assignment(
            service_code=netsgiro.ServiceCode.AVTALEGIRO,
            assignment_type=netsgiro.AssignmentType.TRANSACTIONS,
            number="{:07d}".format(self.id),
            account=self.company_partner_bank_id.acc_number.replace('.',''))

        for payment_line in self.payment_line_ids:
            assignment.add_payment_request(
                kid=payment_line.move_line_id.move_id.line_ids.mapped('contract_id').group_id.ref,
                bank_notification=
                payment_line.move_line_id.move_id.line_ids.mapped('contract_id').group_id.notify_payee,
                due_date=payment_line.date,
                amount=payment_line.amount_currency,
                reference="{:>25}".format(payment_line.name),
                payer_name="{:>10}".format(payment_line.partner_id.ref))
        return transmission.to_ocr().encode('iso-8859-1'), "{}.txt".format(self.name)
