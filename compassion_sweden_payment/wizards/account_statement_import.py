##############################################################################
#
#    Copyright (C) 2015-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        self.ensure_one()
        try:
            Parser = self.env["account.statement.import.bggiro.parser"]
            return Parser.parse(
                 data_file, self.statement_filename
            )
        except ValueError as e:
            _logger.warning(f"Sweden BGgiro parser error {e}", exc_info=True)
        return super()._parse_file(data_file)
