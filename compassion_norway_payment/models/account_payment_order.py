# Copyright 2020 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, exceptions, fields, models
from odoo.exceptions import UserError
import netsgiro
from datetime import date


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def format_transmission_number(self):
        return "{}1".format(self.create_date.strftime("%d%m%y"))

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
            account=self.company_partner_bank_id.acc_number)

        for payment_line in self.payment_line_ids:
            assignment.add_payment_request(
                kid=payment_line.move_line_id.move_id.line_ids.mapped('contract_id').group_id.ref,
                bank_notification=
                payment_line.move_line_id.move_id.line_ids.mapped('contract_id').group_id.notify_payee,
                due_date=payment_line.date,
                amount=payment_line.amount_currency,
                reference=payment_line.name,
                payer_name=payment_line.partner_id.ref)
        return transmission.to_ocr().encode('iso-8859-1'), "{}.xml".format(self.name)
