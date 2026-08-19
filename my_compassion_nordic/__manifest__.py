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
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
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
    "name": "MyCompassion Nordic",
    "summary": "Nordic data & customisation for the my_compassion sponsor portal",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "category": "Website",
    "depends": [
        "my_compassion",
        "payment_adyen",
        "payment_stripe",
        "partner_communication",
        "sponsorship_compassion",
    ],
    "data": [
        "data/digital_fixit_communication.xml",
        "data/portal_invitation.xml",
        "views/payment_provider_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
