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


class LoadMandateWizard(models.Model):
    _inherit = "load.mandate.wizard"
    _description = "Link gifts with letters"

    def generate_new_mandate(self):
        # When we aren't on the norway company we call the parent to try other childrens modules
        if self.env.company.country_id == self.env.ref('base.no'):
            data = list()
            for wizard in self:
                data_dict = {"name_file": wizard.name_file}
                mandate_file = base64.decodebytes(wizard.data_mandate).decode('iso-8859-1')
                try:
                    parsed_file = netsgiro.parse(mandate_file)
                except ValueError as e:
                    raise ValidationError(f"Incorrect File Format{e}")
                for assignment in parsed_file.assignments:
                    for transaction in assignment.transactions:
                        # Variables for the logging of what the process do
                        mandate_id = None
                        old_state = "Active"
                        is_cancelled = False
                        # Actual behaviour
                        res = self.env['recurring.contract.group'].search([('ref', '=', transaction.kid)])
                        partner = res.partner_id
                        res.update({"notify_payee": transaction.notify})
                        if not res:
                            mandate_id = None
                            is_cancelled = None
                            old_state = "Another reference, actual reference : " + transaction.kid
                        elif transaction.registration_type == netsgiro.AvtaleGiroRegistrationType.DELETED_AGREEMENT:
                            mandate_id = partner.valid_mandate_id.id
                            partner.valid_mandate_id.cancel()
                            is_cancelled = True
                        elif transaction.registration_type in (netsgiro.AvtaleGiroRegistrationType.ACTIVE_AGREEMENT,
                                                               netsgiro.AvtaleGiroRegistrationType.NEW_OR_UPDATED_AGREEMENT):
                            old_state = "None"
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
                                mandate_id = mandate.id
                            else:
                                mandate_id = valid.id
                        data_dict['mandate_id'] = mandate_id
                        data_dict['old_mandate_state'] = old_state
                        data_dict['is_cancelled'] = is_cancelled
                        if data_dict['mandate_id'] not in data:
                            data.append(data_dict)
                            data_dict = {}
            self._log_results(data)
            return self.load_views
        else:
            super().generate_new_mandate()
