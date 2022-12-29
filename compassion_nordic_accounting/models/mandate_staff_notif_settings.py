##############################################################################
#
#    Copyright (C) 2016-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models, fields, api


class MandateStaffNotifSettings(models.TransientModel):
    """ Settings configuration for any Notifications."""
    _inherit = "res.config.settings"

    # Users to notify after Disaster Alert
    mandate_notif_id = fields.Many2one(
        "res.users",
        string="Mandate cancelled scheduled activity",
        domain=[("share", "=", False)],
        help="Define which user will be assigned to the scheduled actions.",
        readonly=False,
    )

    def set_values(self):
        super().set_values()
        config = self.env["ir.config_parameter"].sudo()
        config.set_param(
            "compassion_nordic_accounting.mandate_notif_id", str(self.mandate_notif_id.id or 0)
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env["ir.config_parameter"].sudo()
        res["mandate_notif_id"] = int(
            config.get_param("compassion_nordic_accounting.mandate_notif_id", 0)
        )
        return res
