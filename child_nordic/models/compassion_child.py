##############################################################################
#
#    Copyright (C) 2014 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: David Coninckx <david@coninckx.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models, fields


class ChildNordic(models.Model):
    _inherit = "compassion.child"

    description_se = fields.Html("Swedish description")
    description_no = fields.Html("Norwegian translation")
    description_da = fields.Html("Danish translation")
