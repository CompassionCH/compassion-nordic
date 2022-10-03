from odoo import api, models, _


class ChildDescription(models.TransientModel):
    _inherit = "compassion.project.description"

    NORDIC_DESCRIPTIONS = {
        "sv_SE": "desc_se",
        "nb_NO": "desc_no",
        "da_DK": "desc_da",
    }

    @api.model
    def _supported_languages(self):
        res = super()._supported_languages()
        res.update(self.NORDIC_DESCRIPTIONS)
        return res

    def _generate_translation(self):
        # Complete override of description for nordic languages
        project = self.project_id
        field = project.field_office_id
        return f"""
    <table style="border: 0px; margin-bottom: 20px" id="church">
        <tr>
            <td>{_("Church Activities:")}</td><td>{project.get_list("ministry_ids") or _("None")}</td>
        </tr>
        <tr>
            <td>{_("Community Affiliation:")}</td><td>{project.church_denomination}</td>
        </tr>
        <tr>
            <td>{_("Church name:")}</td><td>{project.local_church_name}</td>
        </tr>
    </table>
    <table style="border: 0px; margin-bottom: 20px" id="community">
        <tr>
            <td>{_("Location:")}</td><td>{project.closest_city}, {field.country_id.name}</td>
        </tr>
        <tr>
            <td>{_("Population:")}</td><td>{project.community_population}</td>
        </tr>
        <tr>
            <td>{_("Surroundings:")}</td><td>{project.community_terrain}</td>
        </tr>
        <tr>
            <td>{_("Most common spoken language:")}</td><td>{project.primary_language_id.name}</td>
        </tr>
        <tr>
            <td>{_("Most common jobs:")}</td>
            <td>{project.get_list("primary_adults_occupation_ids.value") or _("None")}</td>
        </tr>
        <tr>
            <td>{_("Local diet:")}</td><td>{project.get_list("primary_diet_ids.value") or _("None")}</td>
        </tr>
    </table>
    <table style="border: 0px; margin-bottom: 20px" id="country">
        <tr>
            <td>{_("Risk area for:")}</td>
            <td>{project.get_list("field_office_id.high_risk_ids.value") or _("None")}</td>
        </tr>
    </table>
"""
