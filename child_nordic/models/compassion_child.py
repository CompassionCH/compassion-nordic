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

    desc_se = fields.Html("Swedish description")
    desc_no = fields.Html("Norwegian translation")
    desc_da = fields.Html("Danish translation")
