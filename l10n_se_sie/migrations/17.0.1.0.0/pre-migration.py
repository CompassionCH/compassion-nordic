def migrate(cr, version):
    cr.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'account_sie_accounts_user_type_fkey'
            ) THEN
                ALTER TABLE account_sie
                DROP CONSTRAINT account_sie_accounts_user_type_fkey;
            END IF;
        END $$;
    """
    )
