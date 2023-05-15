from odoo import models, fields, api

class MyReport(models.Model):
    _name = 'disbursement.data'
    _description = 'Disbursement data'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    month = fields.Date(string='Month', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    fund = fields.Char(string='Fund')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    amount = fields.Float(string='Amount')


    def search(self, args, offset=0, limit=None, order=None, count=False):
        self.env.cr.execute("""
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
            order by month
        """)

        results = self.env.cr.fetchall()
        records = []
        for result in results:
            records.append({
                'company': result[0],
                'month': result[1],
                'account': result[2],
                'fund': result[3],
                'debit': result[4],
                'credit': result[5],
                'amount': result[6],
            })

        return records
