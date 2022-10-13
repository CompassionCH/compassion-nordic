##############################################################################
#
#       ______ Releasing children from poverty      _
#      / ____/___  ____ ___  ____  ____ ___________(_)___  ____
#     / /   / __ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ / __ \/ __ \
#    / /___/ /_/ / / / / / / /_/ / /_/ (__  |__  ) / /_/ / / / /
#    \____/\____/_/ /_/ /_/ .___/\__,_/____/____/_/\____/_/ /_/
#                        /_/
#                            in Jesus' name
#
#    Copyright (C) 2016-2022 Compassion CH (http://www.compassion.ch)
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Compassion Nordic Accounting",
    "summary": "Add Features for nordic Accounting",
    "author": "Compassion CH",
    "website": "http://www.compassion.ch",
    "license": "AGPL-3",
    "category": "Banking addons",
    "depends": ["account_banking_pain_base", "account_banking_mandate", "recurring_contract",
                "account_invoice_pricelist","sponsorship_compassion","partner_ssn","account_statement_import_camt"],
    "data": [
        "views/load_mandate_wizard_view.xml",
        "views/menu_finance_receivables.xml",
        "views/generate_tax_wizard_view.xml",
        'security/ir.model.access.csv'
    ],
    "installable": True,
}
