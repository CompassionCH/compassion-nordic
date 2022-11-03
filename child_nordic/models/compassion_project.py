from odoo import models, fields


class ChildNordic(models.Model):
    _inherit = "compassion.project"

    desc_se = fields.Html("Swedish description")
    desc_no = fields.Html("Norwegian translation")
    desc_da = fields.Html("Danish translation")

    description_left = fields.Text(compute="_compute_description")
    description_right = fields.Text(compute="_compute_description")

    def _compute_description(self):
        lang_map = self.env["compassion.project.description"]._supported_languages()

        for project in self:
            lang = self.env.lang or "en_US"
            description = getattr(project, lang_map.get(lang), "")
            project.description_right = description
            project.description_left = False
