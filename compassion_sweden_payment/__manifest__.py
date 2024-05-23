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
    "name": "Compassion Sweden Payment",
    "summary": "Create Sweden Direct Debit",
    "version": "14.0.1.4.0",
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "license": "AGPL-3",
    "category": "Banking addons",
    "depends": [
        "compassion_nordic_accounting",
        "account_payment_return_import"  # OCA/account-payment
    ],
    "data": [
        "data/account_payment_method.xml",
        "data/payment.return.reason.csv",
        "data/statement_import_sheet_mapping.xml",
    ],
    "installable": True,
}
