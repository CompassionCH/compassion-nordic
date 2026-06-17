from psycopg2.sql import SQL, Identifier

from odoo import fields, models
from odoo.tools import sql


class DisbursementData(models.Model):
    _name = "disbursement.data"
    _auto = False
    _description = "Disbursement Data"

    company_id = fields.Many2one("res.company", required=True)
    month = fields.Date(required=True)
    account_id = fields.Many2one("account.account", required=True)
    product_id = fields.Many2one("product.product")
    debit = fields.Float(readonly=True)
    credit = fields.Float(readonly=True)
    amount = fields.Float(readonly=True)

    def init(self):
        sql.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL("""
            CREATE OR REPLACE VIEW {table} AS (
            SELECT row_number() over() as id,
                rc.id as company_id,
                date_trunc('month', am."date")::date as month,
                pp.id as product_id,
                aa.id as account_id,
                aa.code_store ->> rc.id::char as account_code,
                sum(aml.debit) as debit,
                sum(aml.credit) as credit,
                sum(aml.debit - aml.credit) as amount
            FROM account_move_line aml
            LEFT JOIN account_move am on am.id = aml.move_id
            LEFT JOIN account_account aa on aa.id = aml.account_id
            LEFT JOIN product_product pp on pp.id = aml.product_id
            LEFT JOIN res_company rc on rc.id = am.company_id
            WHERE am.date > '2022-06-30'
                AND (aa.account_type like 'income%' OR aa.account_type = 'expense')
                AND am.state = 'posted'
                AND (
                    (am.move_type = 'out_invoice' AND am.payment_state = 'paid')
                    OR am.move_type <> 'out_invoice'
                    )
                AND (aa.code_store ->> rc.id::char IN (
                        '74710', '74725', '74730', '74800', '74810')
                     OR aa.code_store ->> rc.id::char LIKE '3%')
            GROUP BY rc.id, date_trunc('month', am."date"), aa.id, account_code,
                pp.id
            HAVING (sum(aml.debit) > 0 OR sum(aml.credit) > 0)
            ORDER BY month)
        """).format(table=Identifier(self._table))
        )
