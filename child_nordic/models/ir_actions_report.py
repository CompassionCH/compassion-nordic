from odoo import models


class Report(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # For unknown reason, res_ids are not passed
        # when called by method report_action().
        if "child_compassion" in report_ref and not res_ids:
            res_ids = self.env.context.get("active_ids")
        return super()._render_qweb_pdf(report_ref, res_ids, data)
