from odoo import api, models


class ChildDescription(models.TransientModel):
    _inherit = "compassion.project.description"

    NORDIC_DESCRIPTIONS = {
        "sv_SE": "desc_se",
        "nb_NO": "desc_no",
        "da_DK": "desc_da",
        "fi_FI": "desc_en",
    }

    @api.model
    def _supported_languages(self):
        res = super()._supported_languages()
        res.update(self.NORDIC_DESCRIPTIONS)
        return res
