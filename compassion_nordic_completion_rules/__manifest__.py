# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Compassion Nordic bank statement completion rules",
    "summary": "Add completion rules for nordic bank statements",
    "version": "14.0.1.0.0",
    # see https://odoo-community.org/page/development-status
    "development_status": "Beta",
    "category": "Accounting",
    "website": "https://github.com/CompassionCH/compassion_nordic",
    "author": "Compassion CH",
    # see https://odoo-community.org/page/maintainer-role for a description of the maintainer role and responsibilities
    "maintainers": ["ecino"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "compassion_nordic_accounting",
        "account_statement_completion",
        "base_search_fuzzy",  # OCA/server-tools
    ],
    "data": [
        "data/completion_rules.xml",
        "data/trigram_index.xml",
    ],
    "demo": [
    ],
    "qweb": [
    ]
}
