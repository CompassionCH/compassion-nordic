##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import re

import netsgiro

from odoo import models


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
            data_recipient=netsgiro.NETS_ID,
        )

        assignment = transmission.add_assignment(
            service_code=netsgiro.ServiceCode.AVTALEGIRO,
            assignment_type=netsgiro.AssignmentType.TRANSACTIONS,
            number=f"{self.id:07d}",
            account=self.company_partner_bank_id.acc_number.replace(".", ""),
        )

        for payment_line in self.payment_line_ids:
            assignment.add_payment_request(
                kid=payment_line.move_line_id.move_id.line_ids.mapped(
                    "contract_id"
                ).group_id.ref
                or payment_line.move_line_id.ref,
                bank_notification=payment_line.move_line_id.move_id.line_ids.mapped(
                    "contract_id"
                ).group_id.notify_payee,
                due_date=payment_line.date,
                amount=payment_line.amount_currency,
                reference=f"{payment_line.name:>25}",
                payer_name=f"{payment_line.partner_id.ref:>10}",
            )
        file_content = transmission.to_ocr()
        file_content_windows = re.sub(r"(?<!\r)\n", "\r\n", file_content)
        return file_content_windows.encode("iso-8859-1"), f"{self.name}.txt"
