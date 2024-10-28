##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models, fields


class StaffNotificationSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wordpress_api_key = fields.Char(config_parameter="wordpress_api.api_key")
