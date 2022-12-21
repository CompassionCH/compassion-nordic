##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

from odoo import api, models, fields
from odoo.exceptions import UserError


class GenerateTaxWizard(models.TransientModel):
    _name = "generate.tax.wizard"
    _description = "Generate Tax files"

    tax_year = fields.Selection("_year_selection",
                                "Calendar Year",
                                default=str(datetime.today().year - 1),
                                required=True
                                )
    xml_version = fields.Float("XML version", default=8)
    is_sweden = fields.Boolean(default=lambda s: s.env.company.country_id == s.env.ref("base.se"))

    _sql_constraints = [
        ("tax_year_not_in_the_future",
         "CHECK(tax_year < EXTRACT(year FROM CURRENT_DATE))",
         "Year of taxation can't be in the future"),
    ]

    @api.model
    def _year_selection(self):
        curr_year = datetime.today().year
        year_list = []
        while curr_year >= datetime.today().year - 8:
            year_list.append((str(curr_year), str(curr_year)))
            curr_year -= 1
        return year_list

    def generate_tax(self):
        try:
            raise NotImplementedError()
        except NotImplementedError:
            raise UserError("The company that you are on doesn't support this feature.")

    def _validate_vat_company(self, partner, amount):
        state = "valid"
        is_valid, valid_fmt = partner._validate_vat()
        if not partner.vat:
            state = "empty_vat"
        elif not is_valid:
            state = "invalid_vat"
        # Log the entry in the model made for this
        self.env["res.partner.tax.file.result"].create({
            "partner_id": partner.id,
            "tax_company_id": self.env.company.id,
            "tax_year": self.tax_year,
            "yearly_amount": amount,
            "state": state
        })

        if state in ["empty_vat", "invalid_vat"]:
            return False
        return True

    def _validate_partner_tax_eligibility(self, partner, amount):
        state = "valid"
        is_valid, valid_fmt = partner._validate_ssn()
        if not partner.social_sec_nr:
            state = "empty_ssn"
        elif not is_valid:
            state = "invalid_ssn"
        elif valid_fmt in partner._list_has_bday():
            if 0 < datetime.strptime(f"{self.tax_year}-12-31", "%Y-%m-%d").year - valid_fmt.get_birth_date(partner.social_sec_nr).year < 18:
                state = "under_18"
        # Log the entry in the model made for this
        self.env["res.partner.tax.file.result"].create({
            "partner_id": partner.id,
            "tax_company_id": self.env.company.id,
            "tax_year": self.tax_year,
            "yearly_amount": amount,
            "state": state
        })

        if state in ["invalid_ssn", "under_18", "empty_ssn"]:
            return False
        return True

    def _del_old_entry(self):
        to_del = self.env["res.partner.tax.file.result"].search([("tax_company_id", "=", self.env.company.id)])
        to_del.sudo().unlink()
