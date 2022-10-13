##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        self.ensure_one()
        try:
            Parser = self.env["account.statement.import.beservice.parser"]
            return Parser.parse(
                 data_file, self.statement_filename
            )
        except Exception:
            if self.env.context.get("account_statement_import_paypal_test"):
                raise
            _logger.warning("PayPal parser error", exc_info=True)
        return super()._parse_file(data_file)
