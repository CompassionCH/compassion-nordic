##############################################################################
#
#    Copyright (C) 2014-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand
#
#    The licence is in the file __manifest__.py
#
##############################################################################


from functools import reduce

from odoo import api, fields, models, _


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    notify_payee = fields.Boolean('Notify Payee',
                                  default=False, required=True)


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    @api.model
    def create(self, vals):
        group = self.env['recurring.contract.group'].browse(vals.get('group_id'))
        if group.payment_mode_id.payment_method_code == "norway_direct_debit":
            if vals.get('reference', '/') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'recurring.contract.ref')
            partner_ref = self.env['res.partner'].browse(vals.get('partner_id')).ref
            ref = f'7{partner_id:05d}{int(vals["reference"][3:]):07d}'
            check_digit = (10 - reduce(lambda a, b: (a + int(b / 10) + b),
                                       map(lambda b: (2 if (b[0] & 1 == 0) else 1) * int(b[1]), enumerate(ref)),
                                       0)) % 10
            group.update({'ref': f"{ref}{check_digit}"})
        return super().create(vals)
