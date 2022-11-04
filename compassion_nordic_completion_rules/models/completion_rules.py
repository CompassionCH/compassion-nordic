##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: David Wulliamoz <dwulliamoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import models, fields


_logger = logging.getLogger(__name__)


class StatementCompletionRule(models.Model):
    """ Rules to complete account bank statements."""

    _inherit = "account.statement.completion.rule"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################

    function_to_call = fields.Selection(
        selection_add=[
            ("set_suspense_acc", "Nordic: set bank lines to suspense account"),
            ("get_partner_from_phone_swish", "Nordic: find partner from phone for swish statements"),
            ("get_partner_fuzzy", "Nordic: find partner based on fuzzy search on name"),
            ("get_partner_swedbank", "Nordic: find partner based on child reference in Swedbank statements")
        ], ondelete={
            'set_suspense_acc': 'cascade',
            'get_partner_from_phone_swish': 'cascade',
            'get_partner_fuzzy': 'cascade',
            'get_partner_swedbank': 'cascade',
        }
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
                    return {"account_id": journal_id.suspense_account_id.id}
        return {}

    def get_partner_from_phone_swish(self, stmt_vals, st_line_vals):
        res = {}
        phone_number = st_line_vals.get("narration")
        sweden = self.env.ref("base.se").id
        if phone_number:
            phone_strip = int(phone_number.strip("+46").replace(" ", ""))
            self.env.cr.execute(""" 
                SELECT id FROM res_partner
                WHERE replace(phone, ' ', '') LIKE '%%%s'
                OR replace(mobile, ' ', '') LIKE '%%%s'
                AND country_id = %s
                ORDER BY number_sponsorships DESC;
            """, [phone_strip, phone_strip, sweden])
            partner_id = self.env.cr.fetchone()
            if partner_id:
                res["partner_id"] = partner_id
        return res

    def get_partner_fuzzy(self, stmt_vals, st_line_vals):
        res = {}
        partner_name = st_line_vals.get("partner_name")
        # Use SQL query to allow similarity ordering
        self.env.cr.execute("""
            SELECT id, similarity(name, %s) AS sml FROM res_partner
            WHERE name %% %s
            ORDER BY sml DESC
            LIMIT 1;
        """, [partner_name] * 2)
        row = self.env.cr.fetchone()
        if row:
            partner_id = row[0]
            phone_number = st_line_vals.get("narration")
            if phone_number and phone_number[1:].isdigit():
                if self._swish_update_partner_mobile(stmt_vals, partner_id, phone_number):
                    res["narration"] = phone_number + "\n(updated on the matched partner)."
            res["partner_id"] = partner_id
        return res

    def get_partner_swedbank(self, stmt_vals, st_line_vals):
        res = {}
        transaction_type = st_line_vals.get("payment_ref")
        if transaction_type in ("Insättning", "Överföring"):
            child_ref = st_line_vals.get("ref")
            if child_ref:
                if len(child_ref) == 9:
                    # Insert 0 to the old ref
                    child_ref = child_ref[:2] + "0" + child_ref[2:5] + "0" + child_ref[5:]
                child = self.env["compassion.child"].search([("local_id", "=", child_ref)])
                if child and child.sponsorship_ids:
                    res["partner_id"] = child.sponsorship_ids[0].partner_id.id
        return res

    def _swish_update_partner_mobile(self, stmt_vals, partner_id, phone):
        # Creates a message for logging the action.
        partner = self.env["res.partner"].browse(partner_id)
        p_link = partner._notify_get_action_link("view")
        if not partner.mobile:
            partner.mobile = phone
            partner.message_post(
                body="Mobile phone number automatically updated from Swish bank statement")
            messages = stmt_vals.get("message_ids", [])
            messages.append((0, 0, {
                "author_id": self.env.user.partner_id.id,
                "message_type": "notification",
                "body": f"Mobile phone of partner <a href='{p_link}'>{partner.name}</a> was updated.",
                "email_from": self.env.user.email,
                "model": "account.bank.statement",
            }))
            stmt_vals["message_ids"] = messages
            return True
        return False
