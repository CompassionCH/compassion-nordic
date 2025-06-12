from odoo import api, models

from odoo.addons.l10n_se_sie4_export.models.account_general_ledger import (
    DATEFORMAT_SIE4,
)


class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    @api.model
    def _export_l10n_se_sie4_chart_of_account(self, options):
        # Override the method to filter out off-balance accounts
        return super(
            AccountGeneralLedger, self.with_context(filter_off_balance=True)
        )._export_l10n_se_sie4_chart_of_account(options)

    @api.model
    def _export_l10n_se_sie4_bs_balance(self, options):
        # Override the method to filter out off-balance accounts
        return super(
            AccountGeneralLedger, self.with_context(filter_off_balance=True)
        )._export_l10n_se_sie4_bs_balance(options)

    @api.model
    def _export_l10n_se_sie4_pl_balance(self, options):
        # Override the method to filter out off-balance accounts
        return super(
            AccountGeneralLedger, self.with_context(filter_off_balance=True)
        )._export_l10n_se_sie4_pl_balance(options)

    @api.model
    def _export_l10n_se_sie4_verification(self, options):
        """
        Unfortunately, the parent method cannot be patched to filter out
        off-balance accounts, so we override it completely.
        """
        sie4_verification_lines = []
        dates = self._get_l10n_se_sie4_dates(options)
        company_id = options["companies"][0]["id"]
        unsupported_display_type = {"line_note", "line_section"}
        moves = self.env["account.move"].search(
            [
                *self.env["account.move"]._check_company_domain(company_id),
                ("state", "=", "posted"),
                ("date", ">=", dates["curr_date_from"]),
                ("date", "<=", dates["curr_date_to"]),
            ]
        )

        for verification_idx, move in enumerate(moves.sorted(reverse=True), start=1):
            transactions = []
            for line in move.line_ids:
                if (
                    line.display_type not in unsupported_display_type
                    and not line.account_id.is_off_balance
                ):
                    transactions.append(
                        f"    #TRANS {line.account_id.code} {{}} {line.balance}"
                    )

            sie4_verification_lines.extend(
                (
                    f"#VER A {verification_idx} {move.date.strftime(DATEFORMAT_SIE4)} "
                    f'"{move.name}"',
                    "{",
                    *transactions,
                    "}",
                )
            )

        return sie4_verification_lines
