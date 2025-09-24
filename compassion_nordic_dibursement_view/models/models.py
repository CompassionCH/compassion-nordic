from odoo import fields, models
from odoo.tools import sql


class DisbursementData(models.Model):
    _name = "disbursement.data"
    _auto = False
    _description = "Disbursement Data"

    company = fields.Char(string="Company", required=True, readonly=True)
    month = fields.Date(string="Month", required=True, readonly=True)
    account = fields.Char(string="Account", required=True, readonly=True)
    fund = fields.Char(string="Fund", readonly=True)
    debit = fields.Float(string="Debit", readonly=True)
    credit = fields.Float(string="Credit", readonly=True)
    amount = fields.Float(string="Amount", readonly=True)

    def init(self):
        sql.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
            SELECT row_number() over() as id,
                rc."name" as company,
                date_trunc('month', am."date")::date as month,
                aa.code as account,
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
                AND aa.internal_type = 'other'
                AND am.state = 'posted'
                AND (
                    (am.move_type = 'out_invoice' AND am.payment_state = 'paid')
                    OR am.move_type <> 'out_invoice'
                    )
                AND (aa.code LIKE '7%%' OR aa.code LIKE '3%%')
            GROUP BY rc."name", date_trunc('month', am."date"), aa.code, pp.default_code
            HAVING (sum(aml.debit) > 0 OR sum(aml.credit) > 0)
            ORDER BY month)
        """
            % self._table
        )
