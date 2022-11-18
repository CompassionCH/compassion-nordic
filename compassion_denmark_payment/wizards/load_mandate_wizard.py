##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import csv
from datetime import date

from .. import beservice
from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
import io


class LoadMandateWizard(models.TransientModel):
    _inherit = "load.mandate.wizard"
    _description = "Link gifts with letters"

    def generate_new_mandate(self):
        # When we aren't on the denmark company we call the parent to try other childrens modules
        if self.env.company.country_id == self.env.ref('base.dk'):
            for wizard in self:
                mandate_file = base64.decodebytes(wizard.data_mandate).decode('iso-8859-1')
                try:
                    parsed_file = beservice.parse(mandate_file)
                except Exception as e:
                    raise ValidationError(
                        _(
                            "Incorrect File Format %s"
                        ) % e
                    )
                if parsed_file.delivery_type != beservice.DeliveryType.MANDATE_INFORMATION:
                    raise ValidationError(
                        _(
                            "Incorrect Delivery Type (should be 0603)"
                        )
                    )
                for sections in parsed_file.sections:
                    for info in sections.information_list:
                        partner = self.env['res.partner'].search([('ref', '=', int(info.customer_number))])
                        if info.transaction_code in [beservice.TransactionCode.MANDATE_CANCELLED_BY_BANK,
                                                     beservice.TransactionCode.MANDATE_CANCELLED_BY_BETALINGSSERVICE,
                                                     beservice.TransactionCode.MANDATE_CANCELLED_BY_CREDITOR]:
                            res = self.env['recurring.contract.group'].search([('ref', '=', info.mandate_number)])
                            if not res:
                                raise ValidationError(
                                    _(
                                        "Contract Group '%s' does not exists"
                                    )
                                    % info.mandate_number)
                            partner = res.partner_id
                            partner.valid_mandate_id.cancel()
                        elif info.transaction_code == beservice.TransactionCode.MANDATE_REGISTERED:
                            # we need to update all contract that the sponsor pays with the new mandate number received.
                            active_dd_contract = partner.sponsorship_ids.filtered(
                                lambda a: a.state not in ('terminated', 'cancelled') and a.partner_id == partner.id)
                            payment_mode_id = self.env['account.payment.mode'].search([
                                ('payment_method_id.code','=','denmark_direct_debit')])[0].id
                            for em in active_dd_contract:
                                em.group_id.update({
                                    'ref': info.mandate_number,
                                    'payment_mode_id': payment_mode_id, })
                            company_id = self.env.company.id
                            bank_account = partner.bank_ids.filtered(lambda b: b.acc_number == info.customer_number)
                            if not bank_account:
                                bank_account = self.env["res.partner.bank"].create(
                                    {
                                        "acc_number": info.customer_number,
                                        "partner_id": partner.id,
                                        "company_id": company_id
                                    }
                                )
                            valid = bank_account.mandate_ids.filtered(lambda m: m.state == "valid")

                            if not valid:
                                mandate = self.env["account.banking.mandate"].create(
                                    {
                                        "type": "generic",
                                        "format": "basic",
                                        "partner_bank_id": bank_account.id,
                                        "signature_date": date.today(),
                                        "company_id": company_id,
                                    }
                                )
                                mandate.validate()
        else:
            super().generate_new_mandate()
