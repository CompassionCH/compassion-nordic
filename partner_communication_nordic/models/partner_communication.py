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


from odoo import api, models, _

_logger = logging.getLogger(__name__)


class PartnerCommunication(models.Model):
    _inherit = "partner.communication.job"

    def _fallback_company(self):
        # We always fall back to Sweden
        return self.env["res.company"].browse(2)

    def get_childpack_attachment(self):
        self.ensure_one()
        lang = self.partner_id.lang
        sponsorships = self.get_objects()
        children = sponsorships.mapped("child_id")
        report_name = "partner_communication_compassion.report_child_picture"
        data = {
            "lang": lang,
            "is_pdf": self.send_mode != "physical",
            "type": report_name,
            "doc_ids": children.ids,
        }
        pdf = self._get_pdf_from_data(
            data, self.sudo().env.ref("partner_communication_compassion.report_child_picture")
        )
        return {_("child dossier.pdf"): [report_name, pdf]}

    def send(self):
        """
        - Set onboarding_start_date when first communication is sent
        :return: True
        """
        res = super().send()
        welcome_onboarding = self.env.ref(
            "partner_communication_nordic.config_onboarding_sponsorship_confirmation"
        )
        welcome_comms = self.filtered(
            lambda j: j.config_id == welcome_onboarding
            and j.get_objects().filtered("is_first_sponsorship")
        )
        if welcome_comms:
            welcome_comms.get_objects().write(
                {"onboarding_start_date": datetime.today()}
            )
        return res
