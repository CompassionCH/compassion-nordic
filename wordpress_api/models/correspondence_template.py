##############################################################################
#
#    Copyright (C) 2022 Compassion SC (http://www.compassion.SC)
#    Releasing Children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.SC>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class CorrespondenceTemplate(models.Model):
    _inherit = "correspondence.template"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    layout = fields.Selection(
        [
            ("SC-A-1S11-1", "SC Layout 1"),
            ("SC-A-2S01-1", "SC Layout 2"),
            ("SC-A-3S01-1", "SC Layout 3"),
            ("SC-A-4S01-1", "SC Layout 4"),
            ("SC-A-5S01-1", "SC Layout 5"),
            ("SC-A-6S11-1", "SC Layout 6"),
        ]
    )
