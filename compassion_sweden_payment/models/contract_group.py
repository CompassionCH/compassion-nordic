##############################################################################
#
#    Copyright (C) 2015-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#
#    The licence is in the file __manifest__.py
#
##############################################################################


from functools import reduce
from odoo import models, api, fields


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    @api.model
    def create(self, vals):
        group = self.env['recurring.contract.group'].browse(vals.get('group_id'))
        if group.payment_mode_id.payment_method_code == "sweden_direct_debit":
            if vals.get('reference', '/') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'recurring.contract.ref')
                partner_ref = self.env['res.partner'].browse(vals.get('partner_id')).ref
                ref = f'7{int(partner_ref):05d}{int(vals["reference"][3:]):07d}'
                check_digit = (10 - reduce(lambda a, b: (a + int(b / 10) + b),
                                           map(lambda b: (2 if (b[0] & 1 == 0) else 1) * int(b[1]), enumerate(ref)),
                                           0)) % 10
                group.update({'ref': f"{ref}{check_digit}"})
        return super().create(vals)
