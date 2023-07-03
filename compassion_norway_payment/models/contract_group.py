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

from odoo import fields, models


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    notify_payee = fields.Boolean('Notify Payee', default=False, required=True)

    def set_reference(self, reference):
        super().set_reference(reference)
        if self.payment_mode_id.company_id.country_id == self.env.ref('base.no') and not self.ref:
            partner_ref = self.partner_id.ref
            ref = f'7{int(partner_ref):05d}{int(reference[3:]):07d}'
            check_digit = (10 - reduce(lambda a, b: (a + int(b / 10) + b),
                                       map(lambda b: (2 if (b[0] & 1 == 0) else 1) * int(b[1]), enumerate(ref)),
                                       0)) % 10
            self.ref = f"{ref}{check_digit}"
