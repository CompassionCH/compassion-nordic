from odoo import api, models
from odoo.tools import SQL

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
        # Complete code copied from enterprise waiting for our fix to be merged
        # see https://github.com/odoo/enterprise/pull/122499#event-27434439701
        sie4_verification_lines = []
        report = self.env["account.report"].browse(options.get("report_id"))
        company_ids = report.get_report_company_ids(options)
        query = report._get_report_query(options, "strict_range", [])
        account_alias = query.left_join(
            lhs_alias="account_move_line",
            lhs_column="account_id",
            rhs_table="account_account",
            rhs_column="id",
            link="account_id",
        )
        account_env = self.env["account.account"].with_context(
            allowed_company_ids=company_ids
        )
        account_code = account_env._field_to_sql(account_alias, "code", query)
        sql_query = SQL(
            """
            SELECT m.id                      AS move_id,
                   m.name                    AS move_name,
                   m.date                    AS move_date,
                   %(account_code)s          AS account_code,
                   account_move_line.balance AS balance
            FROM %(table)s
                     JOIN account_move m ON m.id = account_move_line.move_id
            WHERE %(where_clause)s
            ORDER BY m.date ASC, m.name ASC, m.id ASC, account_move_line.id ASC
            """,
            account_code=account_code,
            table=query.from_clause,
            where_clause=query.where_clause,
        )
        self.env.flush_all()
        self.env.cr.execute(sql_query)
        last_move_id = None
        verification_idx = 0
        for row in self.env.cr.dictfetchall():
            current_move_id = row["move_id"]
            if current_move_id != last_move_id:
                if last_move_id is not None:
                    sie4_verification_lines.append("}")
                verification_idx += 1
                move_date_str = row["move_date"].strftime(DATEFORMAT_SIE4)
                sie4_verification_lines.extend(
                    (
                        f'#VER A {verification_idx} {move_date_str} '
                        f'"{row["move_name"]}"',
                        "{",
                    )
                )
                last_move_id = current_move_id
            sie4_verification_lines.append(
                f'    #TRANS {row["account_code"]} {{}} {row["balance"]}'
            )
        if last_move_id is not None:
            sie4_verification_lines.append("}")
        return sie4_verification_lines
