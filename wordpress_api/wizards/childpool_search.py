from odoo import api, models

from odoo.addons.child_compassion.models.compassion_hold import HoldType


class ChildpoolSearch(models.TransientModel):
    _inherit = "compassion.childpool.search"

    @api.model
    def hold_children_for_wordpress(self, take=10):
        wizard = self.create({"take": take})
        wizard.rich_mix()
        if wizard.global_child_ids:
            hold_wizard = self.env["child.hold.wizard"].with_context({"active_id": wizard.id}).create([{
                "type": HoldType.E_COMMERCE_HOLD.value,
                "channel": "web",
                "primary_owner": self.env.user.id,
                "expiration_date": self.env["compassion.hold"].get_default_hold_expiration(HoldType.E_COMMERCE_HOLD)
            }])
            hold_wizard.send()
        return True
