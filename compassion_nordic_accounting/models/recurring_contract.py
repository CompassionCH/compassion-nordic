##############################################################################
#
#    Copyright (C) 2014-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand
#
#    The licence is in the file __manifest__.py
#
##############################################################################


from functools import reduce

from odoo import api, fields, models, _


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    company_id = fields.Many2one(
        # Show selection of all companies except Norden (id = 1)
        domain="[('id', '!=', 1)]",
    )

    @api.onchange('partner_id')
    def change_price(self):
        if self.partner_id.property_product_pricelist.exists():
            for f in self.contract_line_ids:
                f.recompute_price(self.partner_id.property_product_pricelist)
