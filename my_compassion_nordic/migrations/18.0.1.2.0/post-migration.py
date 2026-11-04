from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Turn the SSN flag on for the companies whose country files a gift
    report. New in 18.0.1.2.0, so an existing database has it off
    everywhere and would never ask - the post_init_hook only runs on a
    fresh install.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._my2_seed_collect_ssn()
