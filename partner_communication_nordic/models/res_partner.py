##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_salutation_sv_SE(self):
        self.ensure_one()
        res = "Hej"
        if self.firstname:
            res += f" {self.firstname},"
        else:
            res += ","
        return res

    def _get_salutation_nb_NO(self):
        self.ensure_one()
        res = "Hei"
        if self.firstname:
            res += f" {self.firstname},"
        else:
            res += ","
        return res

    def _get_salutation_da_DK(self):
        self.ensure_one()
        return self._get_salutation_sv_SE()

    @api.model_create_multi
    def create(self, vals_list):
        # Blacklist partners by default
        partners = super().create(vals_list)
        for partner in partners.filtered("email"):
            self.env["mail.blacklist"].create({
                "email": partner.email
            })
        return partners

    def write(self, vals):
        new_email = vals.get("email")
        if new_email:
            self.env["mail.blacklist"].create({
                "email": new_email
            })
        return super().write(vals)
