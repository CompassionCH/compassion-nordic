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
        while curr_year >= datetime.today().year - 15:
            year_list.append((str(curr_year), str(curr_year)))
            curr_year -= 1
        return year_list

    def generate_tax(self):
        try:
            raise NotImplementedError()
        except NotImplementedError:
            raise UserError("The company that you are on doesn't support this feature.")
