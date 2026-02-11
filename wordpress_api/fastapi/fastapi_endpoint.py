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
        routers = {
            "wordpress": wordpress_router,
            "giving_platform": giving_platform_router,
        }
        if self.app in routers:
            return [routers[self.app]]
        return super()._get_fastapi_routers()
