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

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PartnerCommunication(models.Model):
    _inherit = "partner.communication.job"

    child_ids = fields.Char(compute="_compute_child_ids", store=True)

    @api.depends("object_ids")
    def _compute_child_ids(self):
        for job in self:
            objects = job.get_objects().exists()
            if objects._name == "compassion.child":
                job.child_ids = ",".join(objects.mapped("local_id"))
            elif hasattr(objects, "child_id"):
                job.child_ids = ",".join(objects.mapped("child_id.local_id"))
            else:
                job.child_ids = False

    def _search_child_id(self, operator, value):
        return [("object_id", operator, value)]

    def _fallback_company(self):
        # We always fall back to Sweden
        return self.env["res.company"].browse(2)

    def get_childpack_attachment(self):
        self.ensure_one()
        lang = self.partner_id.lang
        sponsorships = self.get_objects()
        children = sponsorships.mapped("child_id")
        report_name = "child_compassion.report_child_picture"
        data = {
            "lang": lang,
            "is_pdf": self.send_mode != "physical",
            "type": report_name,
            "doc_ids": children.ids,
        }
        pdf = self._get_pdf_from_data(
            data, self.sudo().env.ref("child_compassion.report_child_picture")
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
