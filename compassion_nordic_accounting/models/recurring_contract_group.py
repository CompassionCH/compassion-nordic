##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models


class RecurringContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    ref = fields.Char(compute="_compute_ref", store=True, readonly=False)

    @api.depends("partner_id", "contract_ids")
    def _compute_ref(self):
        """
        Implement custom rules for setting a contract group reference
        @param reference: reference of a contract related to the group.
        @return: Nothing
        """
        pass

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        # Find appropriate company by default
        if self.partner_id.country_id:
            country_company = self.env["res.company"].search(
                [("partner_id.country_id", "=", self.partner_id.country_id.id)], limit=1
            )
            self.company_id = country_company or self.env.company
