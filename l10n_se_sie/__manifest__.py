##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "l10n_se: SIE-import",
    "version": "14.0.0.0.2",
    "summary": "Module for importing SIE-files",
    "category": "Accounting",
    "author": "Vertel AB, Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "images": ["static/description/banner.png"],
    "license": "AGPL-3",
    "contributor": "",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-l10n_se",
    "depends": ["l10n_se", "account_fiscal_year"],
    "data": [
        "data/l10n_se_sie_view.xml",
        "views/account_view.xml",
        "data/l10n_se_sie_data.xml",
        "data/fix_account_type_skf.xml",
        "security/ir.model.access.csv",
    ],
    # 'demo': ['l10n_se_sie_demo.xml'],
    "installable": "True",
    "application": "False",
}
