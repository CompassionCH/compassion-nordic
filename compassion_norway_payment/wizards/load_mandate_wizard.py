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
from datetime import date
import netsgiro
from odoo import models
from odoo.exceptions import ValidationError


class LoadMandateWizard(models.TransientModel):
    _inherit = "load.mandate.wizard"
    _description = "Link gifts with letters"

    def generate_new_mandate(self):
        # When we aren't on the norway company we call the parent to try other childrens modules
        if self.env.company.country_id == self.env.ref('base.no'):
            for wizard in self:
                mandate_file = base64.decodebytes(wizard.data_mandate).decode('iso-8859-1')
                try:
                    parsed_file = netsgiro.parse(mandate_file)
                except ValueError as e:
                    raise ValidationError(f"Incorrect File Format{e}")
                for assignment in parsed_file.assignments:
                    for transaction in assignment.transactions:
                        res = self.env['recurring.contract.group'].search([('ref', '=', transaction.kid)])
                        partner = res.partner_id
                        res.update({"notify_payee": transaction.notify})
                        if transaction.registration_type == netsgiro.AvtaleGiroRegistrationType.DELETED_AGREEMENT:
                            partner.valid_mandate_id.cancel()
                        elif transaction.registration_type in (netsgiro.AvtaleGiroRegistrationType.ACTIVE_AGREEMENT, 
                                                               netsgiro.AvtaleGiroRegistrationType.NEW_OR_UPDATED_AGREEMENT):
                            company_id = self.env.company.id
                            bank_account = partner.bank_ids.filtered(lambda b: b.acc_number == transaction.kid)
                            if not bank_account:
                                bank_account = self.env["res.partner.bank"].create(
                                    {
                                        "acc_number": transaction.kid,
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
