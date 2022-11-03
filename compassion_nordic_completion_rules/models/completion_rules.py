##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: David Wulliamoz <dwulliamoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import re
from odoo import models, fields
from odoo.addons.sponsorship_compassion.models.product_names import (
    GIFT_CATEGORY,
    GIFT_REF,
)

import logging

logger = logging.getLogger(__name__)


class StatementCompletionRule(models.Model):
    """ Rules to complete account bank statements."""

    _inherit = "account.statement.completion.rule"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################

    function_to_call = fields.Selection(
        selection_add=[
            ("set_suspense_acc", "Compassion: set bank lines to suspense account"),
        ], ondelete={'set_suspense_acc': 'set null'}
    )

    def set_suspense_acc(self, stmts_vals, st_line):
        """ If line is reconciled in another bankstatement. The account is set directly as suspense account """

        journal_id = self.env['account.journal'].browse(stmts_vals['journal_id'])
        suspense_strings = [
            "Autogiro inbetalning",
            "Bankgiro inbetalning",
            "Swish +",
            # "Överföring",  # transfert
            # "Pris betalning",  # financial fees
        ]

        if float(st_line["amount"]) >= 0:
            is_suspense = any(s in st_line["payment_ref"] for s in suspense_strings)
            if is_suspense:
                if journal_id.suspense_account_id:
                    return {"account_id": journal_id.suspense_account_id}
        return {}
