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
