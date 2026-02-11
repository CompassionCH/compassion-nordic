from odoo import fields, models

from .giving_platform_router import router as giving_platform_router
from .wordpress_router import router as wordpress_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[
            ("wordpress", "Wordpress Endpoint"),
            ("giving_platform", "Giving Platform Endpoint"),
        ],
        ondelete={"wordpress": "cascade", "giving_platform": "cascade"},
    )

    def _get_fastapi_routers(self):
        if self.app == "wordpress":
            return [wordpress_router]
        if self.app == "giving_platform":
            return [giving_platform_router]
        return super()._get_fastapi_routers()
