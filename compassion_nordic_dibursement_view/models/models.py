from odoo import api, fields, models, tools

class DisbursementData(models.Model):
    _name = 'disbursement.data'
    _auto = False
    _description = 'Disbursement Data'

    company = fields.Char(string='Company', required=True)
    month = fields.Date(string='Month', required=True)
    account = fields.Char(string='Account', required=True)
    fund = fields.Char(string='Fund')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    amount = fields.Float(string='Amount')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'disbursement_data')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW disbursement_data_view AS (
            select rc."name" as company, date_trunc('month', am."date")::date as month,
                aa.code as account, pp.default_code as fund, sum(aml.debit) as debit,
                sum(aml.credit) as credit, sum(aml.debit - aml.credit) as amount
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join account_account aa on aa.id = aml.account_id
            left join product_product pp on pp.id = aml.product_id
            left join res_company rc on rc.id = am.company_id
            where am.date > '2022-06-30' 
                and aa.internal_type = 'other'
                and am.state = 'posted'
                and ((am.move_type = 'out_invoice' and am.payment_state = 'paid') or am.move_type <> 'out_invoice')
                and (aa.code like '7%' or aa.code like '3%')
            group by rc."name", date_trunc('month', am."date"), aa.code, pp.default_code
            having (sum(aml.debit) > 0 or sum(aml.credit) > 0)
            order by month)
            """)
