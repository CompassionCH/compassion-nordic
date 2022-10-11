from odoo.http import request, route, Controller

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
        children = request.env["compassion.child"].sudo().with_context(lang=lang).search([("state", "=", "N")])
        data = children.data_to_json("Wordpress Consignment Child")
        return {
            "ChildList": {
                "Children": data
            }
        }
