from odoo import _, models


class CamtParser(models.AbstractModel):
    """Parser for camt bank statement import files."""

    _inherit = "account.statement.import.camt.parser"

    def parse_transaction_details(self, ns, node, transaction):
        res = super().parse_transaction_details(ns, node, transaction)
        found_node = node.xpath(
            "./ns:RmtInf/ns:Strd/ns:RfrdDocInf/ns:Nb", namespaces={"ns": ns}
        )
        if len(found_node) != 0:
            self.add_value_from_node(
                ns,
                node,
                ["./ns:RmtInf/ns:Strd/ns:RfrdDocInf/ns:Nb"],
                transaction["narration"],
                f"{_('Referred Document Information')} (RmtInf/Strd/RfrdDocInf/Nb)",
            )
        return res
