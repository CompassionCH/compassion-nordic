from odoo import api, fields, models

# Countries whose tax authority lets a donor deduct a gift, and whose report
# the charity - not the donor - files, keyed on the donor's national identity
# number:
#
# - SE: Skatteverket KU65, which requires the full ten-digit personnummer.
# - NO: Skatteetaten's gaver til frivillige organisasjoner (skatteloven
#   § 6-50). A missing or wrong fodselsnummer has the whole record rejected,
#   not merely left unmatched.
# - DK: skatteindberetningsloven § 26, identified per § 52 by CPR-nummer.
#
# Finland is deliberately absent. Its donation deduction covers gifts to
# universities only, so a Finnish entity would have no report to file and
# therefore no lawful purpose for a henkilotunnus under tietosuojalaki 29 §.
# An expansion to Tax-Administration-named associations has been proposed but
# is not in force; when it is, and when the entity holds its naming, Finland
# needs adding here and its henkilotunnus format to SSN_FORMATS (res_partner).
SSN_REPORTING_COUNTRIES = ("SE", "NO", "DK")


class ResCompany(models.Model):
    _inherit = "res.company"

    my2_collect_ssn = fields.Boolean(
        string="Collect social security number",
        help="Ask sponsors of this company's website for their national"
        " identity number on the post-payment details form, so their gift"
        " can be reported to the tax authority and they get their"
        " deduction. Off for a company whose country runs no such scheme:"
        " the number would then have no purpose, and no lawful basis.",
    )

    @api.model
    def _my2_seed_collect_ssn(self):
        """Set the flag from each company's country.

        Run at install and by the 18.0.1.2.0 migration; afterwards the flag
        is staff's to change on the company form. Keyed on the country code
        rather than on a data ref: Nordic companies were created through the
        UI in production and carry no xmlid. The search goes through the
        company's partner because res.company.country_id is a non-stored
        compute that cannot be searched.

        Both directions are written, so a company outside the reporting
        countries (the shared Norden parent) is explicitly off.
        """
        companies = self.sudo().search([])
        reporting = companies.search(
            [("partner_id.country_id.code", "in", SSN_REPORTING_COUNTRIES)]
        )
        reporting.my2_collect_ssn = True
        (companies - reporting).my2_collect_ssn = False
        return reporting
