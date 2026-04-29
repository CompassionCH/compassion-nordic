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

from odoo import _, models
from odoo.exceptions import ValidationError

from . import beservice


class LoadMandateWizard(models.Model):
    _inherit = "load.mandate.wizard"
    _description = "Load mandates for Danish company"

    def generate_new_mandate(self):
        # When we aren't on the denmark company we call the parent
        if self.env.company.country_id != self.env.ref("base.dk"):
            return super().generate_new_mandate()

        data = list()
        for wizard in self:
            mandate_file = base64.decodebytes(wizard.data_mandate).decode("iso-8859-1")
            try:
                parsed_file = beservice.parse(mandate_file)
            except Exception as e:
                raise ValidationError(_("Incorrect File Format")) from e
            if parsed_file.delivery_type != beservice.DeliveryType.MANDATE_INFORMATION:
                raise ValidationError(_("Incorrect Delivery Type (should be 0603)"))
            for sections in parsed_file.sections:
                for info in sections.information_list:
                    # Variables for the logging of what the process do
                    mandate_id = None
                    kid = ""
                    old_state = "Active"
                    is_cancelled = False
                    # Actual behaviour
                    partner = self.env["res.partner"].search(
                        [("ref", "=", int(info.customer_number))]
                    )
                    if partner:
                        if info.transaction_code in [
                            beservice.TransactionCode.MANDATE_CANCELLED_BY_BANK,
                            beservice.TransactionCode.MANDATE_CANCELLED_BY_BETALINGSSERVICE,
                            beservice.TransactionCode.MANDATE_CANCELLED_BY_CREDITOR,
                        ]:
                            is_cancelled = True
                            mandate = partner.valid_mandate_id
                            mandate.cancel()
                            mandate_id = mandate.id
                            # We have to set the payment mode to bank transfer again
                            groups = self.env["recurring.contract.group"].search(
                                [
                                    ("ref", "=", info.mandate_number),
                                    ("has_active_contracts", "=", True),
                                ]
                            )
                            if groups:
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
                                groups.write({"payment_mode_id": payment_mode_id})
                        elif (
                            info.transaction_code
                            == beservice.TransactionCode.MANDATE_REGISTERED
                        ):
                            old_state = "None"
                            # we need to update all contract that the sponsor
                            # pays with the new mandate number received.
                            payment_mode_id = (
                                self.env["account.payment.mode"]
                                .search(
                                    [
                                        (
                                            "payment_method_id.code",
                                            "=",
                                            "denmark_direct_debit",
                                        )
                                    ],
                                    limit=1,
                                )
                                .id
                            )
                            groups = self.env["recurring.contract.group"].search(
                                [
                                    ("partner_id", "=", partner.id),
                                    ("has_active_contracts", "=", True),
                                ]
                            )
                            groups.write(
                                {
                                    "ref": info.mandate_number,
                                    "payment_mode_id": payment_mode_id,
                                }
                            )
                            company_id = self.env.company.id
                            bank_account = partner.bank_ids.filtered(
                                lambda b, i=info: b.acc_number == i.customer_number
                            )
                            if not bank_account:
                                bank_account = self.env["res.partner.bank"].create(
                                    {
                                        "acc_number": info.customer_number,
                                        "partner_id": partner.id,
                                        "company_id": company_id,
                                        "allow_out_payment": True,
                                    }
                                )
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
                    else:
                        old_state = "error"
                        kid = info.customer_number

                    data_dict = {
                        "name_file": wizard.name_file,
                        "mandate_id": mandate_id,
                        "old_mandate_state": old_state,
                        "is_cancelled": is_cancelled,
                        "partner_id": partner.id,
                        "kid": kid,
                    }
                    if data_dict["mandate_id"] not in data:
                        data.append(data_dict)
        self._log_results(data)
        self.unlink()
        return True
