from odoo import models, fields


class ChildNordic(models.Model):
    _inherit = "compassion.child"

    desc_se = fields.Html("Swedish description")
    desc_no = fields.Html("Norwegian translation")
    desc_da = fields.Html("Danish translation")

    description_left = fields.Text(compute="_compute_description")
    description_right = fields.Text(compute="_compute_description")

    def _compute_description(self):
        lang_map = self.env["compassion.child.description"]._supported_languages()

        for child in self:
            lang = self.env.lang or "en_US"
            description = getattr(child, lang_map.get(lang), "")
            child.description_left = description
            child.description_right = False  # Could be used to split the description inside the childpack
