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
#    Copyright (C) 2016-2021 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
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

# pylint: disable=C8101
{
    "name": "Compassion Nordic Communications",
    "version": "16.0.1.0.0",
    "category": "Other",
    "author": "Compassion Switzerland",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "depends": [
        "base_automation",
        "survey",
        "partner_communication_compassion",
    ],
    "external_dependencies": {"python": ["pdf2image"]},
    "data": [
        "report/onboarding_photo_by_post.xml",
        "data/onboarding_process.xml",
        "data/onboarding_survey.xml",
        "views/contract_view.xml",
        "views/field_office_view.xml",
        "views/download_child_pictures_view.xml",
        "views/communication_job_view.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
