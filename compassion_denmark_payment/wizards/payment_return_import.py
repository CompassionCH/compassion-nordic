# Copyright 2016 Tecnativa - Carlos Dauden
# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Luis M. Ontalba
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import _, api, models
_logger = logging.getLogger(__name__)


class PaymentReturnImport(models.TransientModel):
    _inherit = "payment.return.import"

    @api.model
    def _parse_file(self, data_file):
        try:
            Parser = self.env["account.statement.import.beservice.parser"]
            return Parser.with_context(journal_id=self.journal_id.id).parse(
                data_file
            )
        except Exception:
            _logger.warning(_("The file couldn't be parsed by danish beservice parser"), exc_info=True)
        return super()._parse_file(data_file)
