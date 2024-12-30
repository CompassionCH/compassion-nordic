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

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        active_contract = self.env.context.get("contract_id")
        if active_contract:
            contract = self.env["recurring.contract"].browse(active_contract)
            for group in groups:
                group.set_reference(contract.reference)
        return groups

    @api.depends("partner_id", "contract_ids")
    def _compute_ref(self):
        """
        Implement custom rules for setting a contract group reference
        @param reference: reference of a contract related to the group.
        @return: Nothing
        """
        pass

    def set_reference(self, reference):
        """
        Implement custom rules for setting a contract group reference
        @param reference: reference of a contract related to the group.
        @return: Nothing
        """
        pass
