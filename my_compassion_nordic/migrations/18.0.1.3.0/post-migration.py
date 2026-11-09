from odoo import SUPERUSER_ID, api

from odoo.addons.my_compassion_nordic.hooks import _seed_website_settings


def migrate(cr, version):
    """Set the Nordic settings of the existing MyCompassion websites: the
    sponsor-a-child URL (a URL staff already set is kept) and the child list
    order mixing the countries.

    The post_init_hook does the same on a fresh install.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _seed_website_settings(env)
