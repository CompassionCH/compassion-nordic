def migrate(cr, version):
    """
    Insert into account_bank_statement_ir_attachment_rel missing relationships
    """
    cr.execute(
        """
        INSERT INTO account_bank_statement_ir_attachment_rel (
            account_bank_statement_id, ir_attachment_id)
        SELECT DISTINCT abs.id, ia.id
        FROM account_bank_statement abs
            JOIN ir_attachment ia ON ia.res_model = 'account.bank.statement'
            AND ia.res_id = abs.id
        WHERE NOT EXISTS (
            SELECT 1
            FROM account_bank_statement_ir_attachment_rel AS rel2
            WHERE abs.id = rel2.account_bank_statement_id
            AND ia.id = rel2.ir_attachment_id
        )
        """
    )
    # Delete invalid contract groups
    cr.execute(
        """
        DELETE FROM recurring_contract_group
        WHERE company_id = 1
        """
    )
