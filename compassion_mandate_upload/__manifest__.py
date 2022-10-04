# Copyright 2013-2020 Akretion (www.akretion.com)
# Copyright 2014-2020 Tecnativa - Pedro M. Baeza & Antonio Espinosa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Compassion Mandate Upload",
    "summary": "Add button to upload mandate files",
    "version": "14.0.1.3.3",
    "license": "AGPL-3",
    "category": "Banking addons",
    "depends": ["account_banking_pain_base", "account_banking_mandate","recurring_contract","account_invoice_pricelist"],
    "data": [
        "views/load_mandate_wizard_view.xml",
        'security/ir.model.access.csv'
    ],
    "installable": True,
}
