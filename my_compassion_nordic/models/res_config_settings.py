from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sponsor_child_url = fields.Char(
        related="website_id.sponsor_child_url",
        readonly=False,
        string="Sponsor a child link",
        help="Page of the public website where MyCompassion sends a sponsor"
        " who wants to sponsor another child. When empty, the sponsor stays"
        " in MyCompassion, on its list of children waiting for a sponsor.",
    )
