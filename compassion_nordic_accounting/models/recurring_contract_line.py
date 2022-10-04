##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand (robin.berguerand@gmail.com)
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ContractLine(models.Model):
    _inherit = "recurring.contract.line"

    def recompute_price(self, pricelist_id):
        data = pricelist_id.price_get(self.product_id.id, 1)
        self.amount = data[pricelist_id.id]
