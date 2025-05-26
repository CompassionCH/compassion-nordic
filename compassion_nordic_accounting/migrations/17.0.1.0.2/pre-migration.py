def migrate(cr, version):
    """
    Update the country_id field in recurring_contract based on partner_id.
    This is necessary to ensure that all recurring contracts have a valid country_id
    set, especially for those that were created before the country_id field was added.
    """
    cr.execute(
        """
        update recurring_contract set country_id = COALESCE((
            select p.country_id from res_partner p where p.id = partner_id
        ), 196) where country_id is null;
        """
    )
