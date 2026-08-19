from odoo import SUPERUSER_ID, api

from odoo.addons.my_compassion_nordic.hooks import _ensure_digital_modes


def migrate(cr, version):
    """Create the digital payment mode for Stripe providers.

    The post_init hook only ran once at install time. This upgrade adds
    Stripe to the digital provider codes, so existing databases need the
    mode creation pass again.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _ensure_digital_modes(env)
