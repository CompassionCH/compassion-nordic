##############################################################################
#
#    Copyright (C) 2014-2015 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Steve Ferry
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, api, models


# pylint: disable=C8107
class ResPartnerBank(models.Model):
    """This class upgrade the partners.bank to match Compassion needs."""

    _inherit = "res.partner.bank"

    def _account_notify_partner(self, action):
        """
        Post a message on the partner's message feed with the account infos
        """
        self.ensure_one()
        self.partner_id.message_post(
            body=_(f"Account {action}, account no: {self.acc_number or '' }"),
            subject=_(f"Account {action}"),
            type="comment",
        )

    @api.model_create_multi
    def create(self, data):
        """Override function to notify creation in a message"""
        result = super().create(data)
        if not self.env.context.get("tracking_disable"):
            for account in result.filtered("partner_id"):
                account._account_notify_partner("created")
        return result

    def unlink(self):
        """Override function to notify delete in a message"""
        if not self.env.context.get("tracking_disable"):
            for acc in self:
                acc._account_notify_partner("deleted")
        result = super().unlink()
        return result
