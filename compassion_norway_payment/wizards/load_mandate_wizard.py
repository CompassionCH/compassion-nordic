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

from odoo import _, models
from odoo.exceptions import ValidationError


class LoadMandateWizard(models.Model):
    _inherit = "load.mandate.wizard"
    _description = "Load mandates for Norway company"

    def generate_new_mandate(self):
        if self.env.company.country_id != self.env.ref("base.no"):
            return super().generate_new_mandate()

        data = []
        for wizard in self:
            mandate_file = base64.decodebytes(wizard.data_mandate).decode("iso-8859-1")
            try:
                parsed_file = netsgiro.parse(mandate_file)
            except ValueError as e:
                raise ValidationError(_("Incorrect File Format")) from e

            for assignment in parsed_file.assignments:
                for transaction in assignment.transactions:
                    mandate_id, old_state, is_cancelled = None, "Active", False
                    res = self.env["recurring.contract.group"].search(
                        [("ref", "=", transaction.kid)]
                    )
                    partner = res.partner_id
                    res.update({"notify_payee": transaction.notify})

                    if not res:
                        old_state, partner = (
                            "Payment option not found",
                            self.env["res.partner"],
                        )
                    elif (
                        transaction.registration_type
                        == netsgiro.AvtaleGiroRegistrationType.DELETED_AGREEMENT
                    ):
                        bank_account = partner.bank_ids.filtered(
                            lambda b, t=transaction: b.acc_number == t.kid
                        )
                        mandates = bank_account.mandate_ids
                        for m in mandates.filtered(
                            lambda _m: _m.state in ["valid", "draft"]
                        ):
                            m.cancel()
                            m.partner_bank_id.write({"active": False})
                            is_cancelled = True
                        payment_mode_id = (
                            self.env["account.payment.mode"]
                            .search(
                                [
                                    ("payment_method_id.code", "=", "manual"),
                                    ("company_id", "=", self.env.company.id),
                                ],
                                limit=1,
                            )
                            .id
                        )
                        res.update({"payment_mode_id": payment_mode_id})
                        if not is_cancelled:
                            old_state = "Mandate might already been deleted"
                    else:
                        old_state = "None"
                        company_id = self.env.company.id
                        bank_account = (
                            self.env["res.partner.bank"]
                            .with_context(active_test=False)
                            .search([("acc_number", "=", transaction.kid)])
                        )
                        payment_mode_id = (
                            self.env["account.payment.mode"]
                            .search(
                                [
                                    (
                                        "payment_method_id.code",
                                        "=",
                                        "norway_direct_debit",
                                    )
                                ],
                                limit=1,
                            )
                            .id
                        )
                        res.update({"payment_mode_id": payment_mode_id})

                        if not bank_account:
                            bank_account = self.env["res.partner.bank"].create(
                                {
                                    "acc_number": transaction.kid,
                                    "partner_id": partner.id,
                                    "company_id": company_id,
                                    "allow_out_payment": True,
                                }
                            )
                        else:
                            if "cancel" in bank_account.mandate_ids.mapped("state"):
                                old_state = "cancelled"
                            if "valid" in bank_account.mandate_ids.mapped("state"):
                                old_state = "valid"
                            if not bank_account.active:
                                bank_account.active = True

                        valid = bank_account.mandate_ids.filtered(
                            lambda m: m.state == "valid"
                        )
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
                            old_state = "valid"

                    data_dict = {
                        "name_file": wizard.name_file,
                        "mandate_id": mandate_id,
                        "old_mandate_state": old_state,
                        "is_cancelled": is_cancelled,
                        "kid": transaction.kid,
                        "partner_id": partner.id,
                    }
                    if data_dict["mandate_id"] not in data:
                        data.append(data_dict)

        self._log_results(data)
        self.unlink()
