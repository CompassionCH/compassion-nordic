from odoo import models, fields


class ChildNordic(models.Model):
    _inherit = "compassion.project"

    desc_se = fields.Html("Swedish description")
    desc_no = fields.Html("Norwegian translation")
    desc_da = fields.Html("Danish translation")
