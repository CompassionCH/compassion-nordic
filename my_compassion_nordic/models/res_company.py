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
# is not in force; when it is, and when the entity holds its naming, turning
# the flag on is all this needs.
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

        Keyed on the country code rather than on a data ref: Nordic companies
        were created through the UI in production and carry no xmlid.

        Filtered in Python, not by domain. res.company.country_id is related
        through partner_id, and a ("country_id.code", "in", ...) domain does
        not filter on it at all - it silently matches every company, which
        would turn the flag on for the shared Norden parent whose country is
        neither Nordic nor a reporting one.

        Both directions are written: this runs once per install/upgrade, and
        a company that gains or loses a reporting country should follow.
        """
        companies = self.sudo().search([])
        reporting = companies.filtered(
            lambda c: c.country_id.code in SSN_REPORTING_COUNTRIES
        )
        reporting.my2_collect_ssn = True
        (companies - reporting).my2_collect_ssn = False
        return reporting
