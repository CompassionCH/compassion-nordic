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

from odoo import api, fields, models


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    notify_payee = fields.Boolean(default=False, required=True)

    @api.depends("partner_id", "contract_ids")
    def _compute_ref(self):
        res = super()._compute_ref()
        for group in self:
            if (
                group.company_id.country_id == self.env.ref("base.no")
                and group.contract_ids
                and not group.ref
            ):
                partner_ref = group.partner_id.ref
                reference = group.contract_ids[:1].reference
                ref = f"7{int(partner_ref):05d}{int(reference[3:]):07d}"
                check_digit = (
                    10
                    - reduce(
                        lambda a, b: (a + int(b / 10) + b),
                        map(
                            lambda b: (2 if (b[0] & 1 == 0) else 1) * int(b[1]),
                            enumerate(ref),
                        ),
                        0,
                    )
                ) % 10
                group.ref = f"{ref}{check_digit}"
        return res
