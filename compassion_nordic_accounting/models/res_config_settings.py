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

    # Users to notify on the scheduled activities of the mandate import
    mandate_notif_id = fields.Many2one(
        "res.users",
        string="Mandate cancelled scheduled activity",
        domain=[("share", "=", False)],
        help="Define which user will be assigned to the scheduled actions.",
        readonly=False,
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        res["mandate_notif_id"] = int(self.get_param_multi_company("compassion_nordic_accounting.mandate_notif"))
        return res

    def set_values(self):
        self._set_param_multi_company("compassion_nordic_accounting.mandate_notif", str(self.mandate_notif_id.id))
        super().set_values()
