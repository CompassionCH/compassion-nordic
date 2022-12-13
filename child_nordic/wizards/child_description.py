##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, models

from odoo.addons.child_compassion.wizards.child_description import ChildDescription


ChildDescription.his_lang.update(
    {
        "sv_SE": {
            "M": [["sin"] * 3, ["sina"] * 3],
            "F": [["sin"] * 3, ["sina"] * 3]
        },
        "nb_NO": {
            "M": [["sin"] * 3, ["sine"] * 3],
            "F": [["sin"] * 3, ["sine"] * 3]
        },
        "da_DK": {
            "M": [["sin"] * 3, ["sine"] * 3],
            "F": [["sin"] * 3, ["sine"] * 3],
        },
    }
)

ChildDescription.he_lang.update(
    {
        "sv_SE": {
            "M": [["han"] * 3, ["de"] * 3],
            "F": [["hon"] * 3, ["dom"] * 3]
        },
        "nb_NO": {
            "M": [["han"] * 3, ["de"] * 3],
            "F": [["hun"] * 3, ["de"] * 3]
        },
        "da_DK": {
            "M": [["han"] * 3, ["de"] * 3],
            "F": [["hun"] * 3, ["de"] * 3],
        },
    }
)

ChildDescription.home_based_lang.update(
    {
        "sv_SE": {
            "M": "{preferred_name} deltar i det hembaserade programmet för de yngsta barnen.",
            "F": "{preferred_name} deltar i det hembaserade programmet för de yngsta barnen."
        },
        "nb_NO": {
            "M": "{preferred_name} deltar i det hjemmebaserte programmet for de minste barna.",
            "F": "{preferred_name} deltar i det hjemmebaserte programmet for de minste barna."
        },
        "da_DK": {
            "M": "{preferred_name} deltager i det hjemmebaserede program for de mindste børn.",
            "F": "{preferred_name} deltager i det hjemmebaserede program for de mindste børn."
        },
    }
)

ChildDescription.school_no_lang.update(
    {
        "sv_SE": {
            "M": "{preferred_name} går inte i skolan.",
            "F": "{preferred_name} går inte i skolan.",
        },
        "nb_NO": {
            "M": "{preferred_name} går ikke i skole.",
            "F": "{preferred_name} går ikke i skole.",
        },
        "da_DK": {
            "M": "{preferred_name} går ikke på skolen.",
            "F": "{preferred_name} går ikke på skolen.",
        },
    }
)

ChildDescription.duties_intro_lang.update(
    {
        "sv_SE": {
            "M": "Hemma hjälper han till med följande sysslor:",
            "F": "Hemma hjälper hon till med följande sysslor:",
        },
        "nb_NO": {
            "M": "Hjemme hjelper han til med følgende gjøremål:",
            "F": "Hjemme hjelper hun til med følgende gjøremål:",
        },
        "da_DK": {
            "M": "Hjemme hjælper han med følgende opgaver:",
            "F": "Hjemme hjælper hun med følgende opgaver:",
        },
    }
)

ChildDescription.church_intro_lang.update(
    {
        "sv_SE": {
            "M": "I kyrkan deltar han i följande aktiviteter:",
            "F": "I kyrkan deltar hon i följande aktiviteter:",
        },
        "nb_NO": {
            "M": "I kirken deltar han i følgende aktiviteter:",
            "F": "I kirken deltar hun i følgende aktiviteter:",
        },
        "da_DK": {
            "M": "I kirken deltager han i følgende aktiviteter:",
            "F": "I kirken deltager hun i følgende aktiviteter:",
        },
    }
)

ChildDescription.hobbies_intro_lang.update(
    {
        "sv_SE": {
            "M": "Hans favoritaktiviteter är:",
            "F": "Hennes favoritaktiviteter är:",
        },
        "nb_NO": {
            "M": "Hans favorittaktiviteter er:",
            "F": "Hendes favorittaktiviteter er:",
        },
        "da_DK": {
            "M": "Hans yndlingsaktiviteter er:",
            "F": "Hendes yndlingsaktiviteter er:",
        },
    }
)

ChildDescription.handicap_intro_lang.update(
    {
        "sv_SE": {
            "M": "{preferred_name} lider av:",
            "F": "{preferred_name} lider av:",
        },
        "nb_NO": {
            "M": "{preferred_name} lider av:",
            "F": "{preferred_name} lider av:",
        },
        "da_DK": {
            "M": "{preferred_name} lider af:",
            "F": "{preferred_name} lider af:",
        },
    }
)


class ChildDescriptionCH(models.TransientModel):
    _inherit = "compassion.child.description"

    @api.model
    def _supported_languages(self):
        """
        Inherit to add more languages to have translations of
        descriptions.
        {lang: description_field}
        """
        return {
            "en_US": "desc_en",
            "nb_NO": "desc_no",
            "sv_SE": "desc_se",
            "da_DK": "desc_da",
            "fi_FI": "desc_en"
        }
