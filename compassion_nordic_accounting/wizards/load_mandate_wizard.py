##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import csv

from odoo import api, models, fields, _
from odoo.exceptions import UserError
import io


class LoadMandateWizard(models.TransientModel):
    _name = "load.mandate.wizard"
    _description = "Link gifts with letters"
    _order = "create_date desc"

    data_mandate = fields.Binary("Mandate file")
    name_file = fields.Char("File Name")
    company_id = fields.Many2one(
        "res.company",
        "Company",
        compute="_compute_all",
        store=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        "Partner",
        compute="_compute_all",
        store=True
    )
    mandate_id = fields.Many2one(
        "account.banking.mandate",
        "Mandate",
        check_company=True,
    )
    old_mandate_state = fields.Char()
    current_mandate_state = fields.Char(compute="_compute_all", store=True)

    @api.depends('mandate_id')
    def _compute_all(self):
        for rec in self:
            rec.partner_id = rec.mandate_id.partner_id
            rec.company_id = rec.mandate_id.company_id
            rec.current_mandate_state = rec.mandate_id.state

    def generate_new_mandate(self):
        try:
            raise NotImplementedError()

        except NotImplementedError:
            raise UserError(_("The company that you are on doesn't support this feature."))

    def _log_results(self, vals_list):
        for vals in vals_list:
            if vals.get('mandate_id'):
                self.env['load.mandate.wizard'].create(vals)
