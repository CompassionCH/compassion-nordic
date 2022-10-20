import json

from werkzeug.exceptions import NotFound, BadRequest

from odoo.http import request, route, Controller

from odoo.addons.child_compassion.models.compassion_hold import HoldType
from odoo.addons.sbc_compassion.models.correspondence_page import PAGE_SEPARATOR

LANG_MAPPING = {
    "ENG": "en_US",
    "SVE": "sv_SE",
    "NOR": "nb_NO",
    "DAK": "da_DK"
}


class ApiController(Controller):

    @route("/wapi/consignment", auth="public", methods=["GET"], type="json")
    def get_consigned_children(self, **params):
        lang = LANG_MAPPING.get(params.get("LanguageCode", "ENG"))
        limit = int(params.get("limit", 0))
        offset = int(params.get("offset", 0))
        count = request.env["compassion.child"].sudo().search_count([
            ("state", "=", "N"), ("hold_channel", "=", "web"), ("hold_type", "=", HoldType.E_COMMERCE_HOLD.value)
        ])
        children = request.env["compassion.child"].sudo().with_context(lang=lang).search([
            ("state", "=", "N"), ("hold_channel", "=", "web"), ("hold_type", "=", HoldType.E_COMMERCE_HOLD.value)
        ], limit=limit, offset=offset)
        data = children.data_to_json("Wordpress Consignment Child")
        for child_vals in data:
            try:
                child_vals["localSociatySituated"] = child_vals["localSociatySituated"] + ", " + child_vals.pop(
                    "country_name")
                member_ids = child_vals["householdMember"]
                caregivers = children.env["compassion.household.member"].browse(member_ids).filtered("is_caregiver")
                child_vals["householdMember"] = caregivers.get_list("role")
            except (KeyError, TypeError):
                continue
        return {
            "ChildList": {
                "count": count,
                "range": f"{offset}-{offset + (limit-1)}" if limit else "ALL",
                "children": data
            }
        }

    @route("/wapi/consignment/<string:global_id>/sponsor", auth="public", methods=["GET"], type="json")
    def sponsor_child(self, global_id, **params):
        wordpress_user = request.env.ref("wordpress_api.user_wordpress")
        child = request.env["compassion.child"].with_user(wordpress_user).search([("global_id", "=", global_id)])
        if not child:
            raise NotFound
        child.hold_id.write({
            "type": HoldType.NO_MONEY_HOLD.value,
            "expiration_date": child.hold_id.get_default_hold_expiration(HoldType.NO_MONEY_HOLD)
        })
        return f"Child {global_id} is sponsored"

    @route("/wapi/letters/write", auth="public", methods=["POST"], type="json")
    def write_letter(self, InputTxt, **params):
        try:
            letter_data = json.loads(InputTxt)
            child_global_id = letter_data["Beneficiary"]["GlobalBeneficiaryId"]
            sponsor_global_id = letter_data["Supporter"].get("GlobalSupporterId", "not_set")
            sponsor_ref = letter_data["Supporter"]["CompassConstituentId"]
            original_text = PAGE_SEPARATOR.join(map(lambda p: p.get("OriginalText", ""), letter_data["Pages"]))
            original_language = LANG_MAPPING.get(letter_data["OriginalLanguage"], "sv_SE")
            letter_image = letter_data["PDFBase64"]
        except (TypeError, ValueError, KeyError):
            raise BadRequest("Input data not valid.")

        wordpress_user = request.env.ref("wordpress_api.user_wordpress")
        sponsorship = request.env["recurring.contract"].with_user(wordpress_user).search([
            "|", ("correspondent_id.global_id", "=", sponsor_global_id),
            ("correspondent_id.ref", "=", sponsor_ref),
            ("child_id.global_id", "=", child_global_id),
            ("state", "not in", ["terminated", "cancelled"])
        ])
        if not sponsorship or len(sponsorship) > 1:
            raise BadRequest("No valid sponsorship found for given Supporter and Beneficiary.")
        language = sponsorship.env["res.lang.compassion"].search([
            ("lang_id.code", "=", original_language)
        ], limit=1)
        new_letter = request.env["correspondence"].with_user(wordpress_user).create([{
            "original_text": original_text,
            "original_language_id": language.id,
            "letter_image": letter_image,
            "sponsorship_id": sponsorship.id,
            "direction": "Supporter To Beneficiary"
        }])
        return f"New letter created with id {new_letter.id}"

    @route("/wapi/supporter/<string:global_id>", auth="public", methods=["GET"], type="json")
    def get_sponsor_info(self, global_id, **params):
        sponsor = request.env["res.partner"].sudo().search([("global_id", "=", global_id)])
        children = sponsor.sponsored_child_ids
        if not sponsor or not children:
            raise NotFound("Not a valid sponsor.")
        return {
            "Supporter": {
                "GlobalSupporterId": sponsor.global_id,
                "CompassConstituentId": sponsor.ref
            },
            "Beneficiaries": [
                {
                    "GlobalBeneficiaryId": child.global_id,
                    "LocalBeneficiaryId": child.local_id,
                    "FirstName": child.firstname,
                    "PreferredName": child.preferred_name,
                    "RelationshipType": "Sponsor"
                }
                for child in children
            ]
        }
