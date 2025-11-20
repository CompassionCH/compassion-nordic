from psycopg2.sql import SQL, Identifier

from odoo import fields, models
from odoo.tools import sql


class DisbursementData(models.Model):
    _name = "disbursement.data"
    _auto = False
    _description = "Disbursement Data"

    company = fields.Char(required=True, readonly=True)
    month = fields.Date(required=True, readonly=True)
    account = fields.Char(required=True, readonly=True)
    fund = fields.Char(readonly=True)
    debit = fields.Float(readonly=True)
    credit = fields.Float(readonly=True)
    amount = fields.Float(readonly=True)

    def init(self):
        sql.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL("""
            CREATE OR REPLACE VIEW {table} AS (
            SELECT row_number() over() as id,
                rc."name" as company,
                date_trunc('month', am."date")::date as month,
                aa.code_store as account,
                pp.default_code as fund,
                sum(aml.debit) as debit,
                sum(aml.credit) as credit,
                sum(aml.debit - aml.credit) as amount
            FROM account_move_line aml
            LEFT JOIN account_move am on am.id = aml.move_id
            LEFT JOIN account_account aa on aa.id = aml.account_id
            LEFT JOIN product_product pp on pp.id = aml.product_id
            LEFT JOIN res_company rc on rc.id = am.company_id
            WHERE am.date > '2022-06-30'
                AND aa.account_type = 'income_other'
                AND am.state = 'posted'
                AND (
                    (am.move_type = 'out_invoice' AND am.payment_state = 'paid')
                    OR am.move_type <> 'out_invoice'
                    )
                AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(aa.code_store) AS elem(value)
                    WHERE elem.value LIKE '7%' OR elem.value LIKE '3%'
                )
            GROUP BY rc."name", date_trunc('month', am."date"), aa.code_store,
                pp.default_code
            HAVING (sum(aml.debit) > 0 OR sum(aml.credit) > 0)
            ORDER BY month)
        """).format(table=Identifier(self._table))
        )
