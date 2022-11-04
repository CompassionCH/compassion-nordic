# Copyright 2022 CompassionCH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    @api.model
    def _convert_line_to_transactions(self, line):  # noqa: C901
        """Push notes into narration field, if empty."""
        notes = line.get("notes")
        res = super()._convert_line_to_transactions(line)
        transaction = res[0]
        if not transaction.get("narration"):
            transaction["narration"] = notes
        return res
