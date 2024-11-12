import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ContractLine(models.Model):
    _inherit = "recurring.contract.line"

    def _remove_balance(self):
        balance_product = self.env.ref("recurring_contract.product_balance_migr")
        lines = self.search([("product_id", "=", balance_product.id)])
        _logger.info("Removed %s balance lines", str(len(lines)))
        return lines.unlink()
