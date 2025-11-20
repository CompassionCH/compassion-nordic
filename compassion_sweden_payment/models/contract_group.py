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

from odoo import api, models


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    @api.depends("partner_id", "contract_ids")
    def _compute_ref(self):
        res = super()._compute_ref()
        for group in self:
            if (
                group.company_id.country_id == self.env.ref("base.se")
                and group.contract_ids
                and not group.ref
            ):
                reference = group.contract_ids[:1].reference
                partner_ref = group.partner_id.ref
                ref = f"7{int(partner_ref):05d}{int(reference[3:]):09d}"
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
