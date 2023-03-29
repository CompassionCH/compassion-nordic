##############################################################################
#
#    Copyright (C) 2017 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, models


class ChildDescription(models.TransientModel):
    _inherit = "compassion.project.description"

    NORDIC_DESCRIPTIONS = {
        "sv_SE": "desc_se",
        "nb_NO": "desc_no",
        "da_DK": "desc_da",
        "fi_FI": "description_en",
    }

    @api.model
    def _supported_languages(self):
        res = super()._supported_languages()
        res.update(self.NORDIC_DESCRIPTIONS)
        return res
