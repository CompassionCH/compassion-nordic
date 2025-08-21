from openupgradelib import openupgrade


def migrate(cr, version):
    cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = 'wordpress_api' AND name = 'user_wordpress'
        """
    )
    res = cr.fetchone()
    if not res:
        return
    wordpress_user_id = res[0]
    admin_user_id = 1
    openupgrade.logged_query(
        cr,
        "UPDATE compassion_hold SET primary_owner = %s WHERE primary_owner = %s",
        (admin_user_id, wordpress_user_id),
    )
    openupgrade.logged_query(
        cr,
        "UPDATE ir_cron SET user_id = %s WHERE user_id = %s",
        (admin_user_id, wordpress_user_id),
    )
