# Copyright 2014-2017 Akretion (http://www.akretion.com).
# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
