from odoo import models


class Report(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, res_ids=None, data=None):
        # For unknown reason, res_ids are not passed when called by method report_action().
        if "child_nordic" in self.report_name and not res_ids:
            res_ids = self.env.context.get("active_ids")
        return super()._render_qweb_pdf(res_ids, data)
