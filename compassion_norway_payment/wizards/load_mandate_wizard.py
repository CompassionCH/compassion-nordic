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
    _description = "Load mandates for Norway company"

    def generate_new_mandate(self):
        # When we aren't on the norway company we call the parent to try other childrens modules
        if self.env.company.country_id == self.env.ref('base.no'):
            data = list()
            for wizard in self:
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
                            is_cancelled = None
                            old_state = "Payment option not found"
                            partner = self.env['res.partner']
                        elif transaction.registration_type == netsgiro.AvtaleGiroRegistrationType.DELETED_AGREEMENT:
                            # If the mandate is already cancelled we should avoid error
                            if partner.valid_mandate_id.state in ['valid', 'draft']:
                                partner.valid_mandate_id.cancel()
                                is_cancelled = True
                                payment_mode_id = self.env['account.payment.mode'].search([
                                    ('payment_method_id.code', '=', 'manual'),
                                    ('company_id', '=', self.env.company.id)], limit=1).id
                                res.update({'payment_mode_id': payment_mode_id})
                            else:
                                old_state = "Mandate might already been deleted"
                        elif transaction.registration_type in (netsgiro.AvtaleGiroRegistrationType.ACTIVE_AGREEMENT,
                                                               netsgiro.AvtaleGiroRegistrationType.NEW_OR_UPDATED_AGREEMENT):
                            old_state = "None"
                            company_id = self.env.company.id
                            bank_account = partner.bank_ids.filtered(lambda b: b.acc_number == transaction.kid)
                            # We have to update payment option
                            payment_mode_id = self.env['account.payment.mode'].search([
                                ('payment_method_id.code', '=', 'norway_direct_debit')], limit=1).id
                            res.update({'payment_mode_id': payment_mode_id})
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
                        data_dict = {"name_file": wizard.name_file, 'mandate_id': mandate_id,
                                     'old_mandate_state': old_state, 'is_cancelled': is_cancelled,
                                     'kid': transaction.kid, 'partner_id': partner.id}
                        if data_dict['mandate_id'] not in data:
                            data.append(data_dict)
            self._log_results(data)
            self.unlink()
        else:
            super().generate_new_mandate()
