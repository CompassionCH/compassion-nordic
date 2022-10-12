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

    def contract_waiting(self):
        res = super().contract_waiting()
        self.filtered(lambda c: "S" in c.type and not c.is_active).with_context({})._new_dossier()
        return res

    def _new_dossier(self):
        """
        Sends the dossier of the new sponsorship to both payer and
        correspondent.
        """
        for spo in self:
            if spo.correspondent_id.id != spo.partner_id.id:
                corresp = spo.correspondent_id
                payer = spo.partner_id
                if corresp.contact_address != payer.contact_address:
                    spo._send_new_dossier()
                    spo._send_new_dossier(correspondent=False)
                    continue
            spo._send_new_dossier()

    def _send_new_dossier(self, correspondent=True):
        """
        Sends the New Dossier communications if it wasn't already sent for
        this sponsorship.
        :param correspondent: True if communication is sent to correspondent
        :return: None
        """
        self.ensure_one()
        new_dossier = self.env.ref("partner_communication_nordic.config_onboarding_sponsorship_confirmation")
        print_dossier = self.env.ref("partner_communication_compassion.planned_dossier")
        transfer = self.env.ref("partner_communication_compassion.new_dossier_transfer")
        child_picture = self.env.ref("partner_communication_nordic.config_onboarding_photo_by_post")
        partner = self.correspondent_id if correspondent else self.partner_id
        if self.origin_id.type == "transfer":
            configs = transfer
        elif (
                not partner.email
                or partner.global_communication_delivery_preference == "physical"
        ):
            configs = print_dossier
        else:
            configs = new_dossier + child_picture
        for config in configs:
            already_sent = self.env["partner.communication.job"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("config_id", "=", config.id),
                    ("object_ids", "like", str(self.id)),
                    ("state", "=", "done"),
                ]
            )
            if not already_sent:
                self.with_context({}).send_communication(config, correspondent)
        return True
