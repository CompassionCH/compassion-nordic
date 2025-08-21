from odoo import fields, models

from .wordpress_router import router as wordpress_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("wordpress", "Wordpress Endpoint")],
        ondelete={"wordpress": "cascade"},
    )

    def _get_fastapi_routers(self):
        if self.app == "wordpress":
            return [wordpress_router]
        return super()._get_fastapi_routers()
