from odoo import api, models, _


class ChildDescription(models.TransientModel):
    _inherit = "compassion.child.description"

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
        child = self.child_id
        household = child.household_id
        return f"""
    <table style="border: 0px; margin-bottom: 20px" id="child_info">
        <tr>
            <td>{_("My name is:")}</td><td>{child.preferred_name}</td>
        </tr>
        <tr>
            <td>{_("I am from:")}</td><td>{child.field_office_id.country_id.name}</td>
        </tr>
        <tr>
            <td>{_("Birthday:")}</td><td>{child.get_date("birthdate")}</td>
        </tr>
        <tr>
            <td>{_("Gender:")}</td><td>{child.translate("gender")}</td>
        </tr>
        <tr>
            <td>{_("Guardian:")}</td><td>{household.get_caregivers().get_list("role") or _("None")}</td>
        </tr>
        <tr>
            <td>{_("Children at home:")}</td><td>{household.nb_brothers + household.nb_sisters + 1}</td>
        </tr>
        <tr>
            <td>{_("Compassion No:")}</td><td>{child.local_id}</td>
        </tr>
    </table>
    <table style="border: 0px; margin-bottom: 20px" id="schooling">
        <tr>
            <td>{_("School level:")}</td><td>{child.education_level}</td>
        </tr>
    </table>
    <table style="border: 0px; margin-bottom: 20px" id="activities">
        <tr>
            <td>{_("Helps with:")}</td><td>{child.get_list("duty_ids.value") or _("None")}</td>
        </tr>
        <tr>
            <td>{_("Hobbies:")}</td><td>{child.get_list("hobby_ids.value") or _("None")}</td>
        </tr>
    </table>
"""
