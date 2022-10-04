##############################################################################
#
#    Copyright (C) 2016-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import models, fields

logger = logging.getLogger(__name__)


class RecurringContract(models.Model):
    """
    Add method to send all planned communication of sponsorships.
    """

    _inherit = "recurring.contract"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    onboarding_start_date = fields.Date(
        help="Indicates when the first email of the onboarding process was sent.",
        copy=False,
    )
