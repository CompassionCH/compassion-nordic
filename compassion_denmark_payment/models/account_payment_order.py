# Copyright 2020 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, exceptions, fields, models
from odoo.exceptions import UserError
from datetime import date
from .. import beservice


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def format_transmission_number(self):
        return "{}1".format(self.create_date.strftime("%d%m%y"))

    def generate_payment_file(self):
        self.ensure_one()
        if self.payment_method_id.code != "denmark_direct_debit":
            return super().generate_payment_file()

        data_delivery = beservice.DataDelivery(data_supplier_number=self.payment_mode_id.initiating_party_issuer,
                                               subsystem='BS1', delivery_identification=1)
        data_delivery.add_section(data_supplier_id=self.payment_mode_id.initiating_party_identifier,
                                  pbs_number=self.company_partner_bank_id.acc_number,
                                  debtor_group_number=1)

        for payment_line in self.payment_line_ids:
            val = payment_line.move_line_id.move_id.line_ids.mapped('contract_id')
            data_delivery.sections[0].add_payment(customer_number=f'{payment_line.partner_id.ref:15}',
                                                  mandate_number=payment_line.mandate_id.id,
                                                  amount=payment_line.amount_currency,
                                                  sign_code=beservice.SignCode.COLLECTION,
                                                  payment_date=payment_line.date,
                                                  )
        return data_delivery.to_ocr().encode('iso-8859-1'), "{}.xml".format(self.name)
