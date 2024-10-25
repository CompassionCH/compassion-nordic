##############################################################################
#
#    Copyright (C) 2017 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models, fields


class ChildNordic(models.Model):
    _inherit = "compassion.project"

    description_se = fields.Html("Swedish description")
    description_no = fields.Html("Norwegian translation")
    description_da = fields.Html("Danish translation")
