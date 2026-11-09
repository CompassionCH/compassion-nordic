from odoo import SUPERUSER_ID, api

from odoo.addons.my_compassion_nordic.hooks import _seed_sponsor_child_urls


def migrate(cr, version):
    """Fill the sponsor-a-child URL of the existing MyCompassion websites.

    The post_init_hook does the same on a fresh install. A URL staff already
    set is kept.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _seed_sponsor_child_urls(env)
