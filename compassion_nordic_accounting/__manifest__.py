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
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "version": "17.0.1.0.3",
    "license": "AGPL-3",
    "category": "Banking addons",
    "depends": [
        # compassion-accounting
        "account_reconcile_compassion_ee",
        "account_statement_import_compassion_ee",
        # compassion-modules
        "sponsorship_compassion",
        # OCA/bank-payment
        "account_banking_pain_base",
        "account_banking_mandate",
        "account_payment_order",
        # OCA/partner-contact
        "partner_contact_birthdate",
        # OCA/account-invoicing
        "account_invoice_pricelist",
        # OCA/bank-statement-import
        "account_statement_import_camt",
        # odoo/enterprise
        "l10n_se_sie4_export",
    ],
    "data": [
        "data/general_ledger_offbalance_filter.xml",
        "views/account_move_view.xml",
        "views/load_mandate_wizard_view.xml",
        "views/partner_tax_file_res.xml",
        "views/menu_finance_receivables.xml",
        "views/generate_tax_wizard_view.xml",
        "views/res_partner_view.xml",
        "views/account_statement_import_view.xml",
        "views/mandate_staff_notif_settings_view.xml",
        "views/contracts_view.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
