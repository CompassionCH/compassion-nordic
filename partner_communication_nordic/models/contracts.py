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
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

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
        new_sponsorships = self.filtered(lambda c: "S" in c.type and not c.is_active)
        if new_sponsorships:
            new_sponsorships.with_delay(
                channel="root.partner_communication",
                identity_key=f"{self._name}.send_new_dossier.{new_sponsorships.ids}",
            )._new_dossier()
        return res

    def _new_dossier(self):
        """Sends the dossier of the new sponsorship to both payer and correspondent."""
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
        new_dossier = self.env.ref(
            "partner_communication_nordic.config_onboarding_sponsorship_confirmation"
        )
        print_dossier = self.env.ref("partner_communication_compassion.planned_dossier")
        transfer = self.env.ref("partner_communication_compassion.new_dossier_transfer")
        child_picture = self.env.ref(
            "partner_communication_nordic.config_onboarding_photo_by_post"
        )
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
                    ("state", "!=", "cancel"),
                ]
            )
            if not already_sent:
                self.send_communication(config, correspondent)
        return True

    @api.model
    def cron_generate_birthday_reminders(self):
        logger.info("Creating Birthday Reminder Communications")
        today = datetime.now()
        in_two_month = today + relativedelta(months=2)
        sponsorships_with_birthday_in_two_months = self.search(
            [
                ("child_id", "!=", False),
                ("state", "=", "active"),
                ("child_id.birthdate", "like", in_two_month.strftime("%%-%m-%%")),
                ("type", "=like", "S%"),
                ("pricelist_id.company_id.country_id.code", "=", "SE"),
            ]
        )
        sponsorships_with_birthday_in_two_months._send_birthday_reminders()

    def _send_birthday_reminders(self):
        for sponsorship in self:
            payer = sponsorship.partner_id
            correspondent = sponsorship.correspondent_id
            # Sweden automatic gifts receive the thank you communication instead
            is_sweden_company = (
                sponsorship.pricelist_id.company_id.country_id.code == "SE"
            )
            send_to_payer = payer.email and not (
                is_sweden_company and sponsorship.birthday_invoice
            )
            send_to_correspondent = correspondent != payer and correspondent.email
            if send_to_correspondent or send_to_payer:
                sponsorship.with_delay(
                    channel="root.partner_communication",
                    identity_key=f"{sponsorship._name}."
                    f"send_birthday_reminder.{sponsorship.id}",
                    priority=50,
                ).send_communication(
                    self.env.ref(
                        "partner_communication_nordic.config_birthday_reminder"
                    ),
                    correspondent=send_to_correspondent,
                    both=send_to_payer and send_to_correspondent,
                )
