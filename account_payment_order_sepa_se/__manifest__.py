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
    "name": "Account: Payment Order Sepa Sweden",
    "version": "14.0.0.0.1",
    "summary": "Module that fixes some of the errors that the sepa files triggers "
    "for the SEB parser for Swedish payments",
    "category": "Accounting",
    "author": "Vertel AB,Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "images": ["/static/description/banner.png"],  # 560x280 px.
    "license": "AGPL-3",
    "contributor": "",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/",
    # External Repo https://github.com/OCA/bank-payment
    "depends": [
        "account_banking_pain_base",
        "account_banking_sepa_credit_transfer",
        "account_payment_order",
    ],
    "data": [
        #'views/regulatory_reporting_code.xml',
    ],
    "demo": [],
    "qweb": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
