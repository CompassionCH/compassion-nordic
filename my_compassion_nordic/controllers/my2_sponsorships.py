from odoo import _

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)


class MyCompassionNewSponsorshipNordic(MyCompassionNewSponsorshipController):
    """The Nordic entities ask one more thing on the post-payment details
    form: the payer's national identity number, which is what lets the gift
    be reported to their tax authority so they get their deduction.

    Optional throughout. No Nordic country makes the number a condition of
    donating, and the statutory reporting duty that makes collecting it
    lawful at all is purpose-bound to that report - so a sponsor who leaves
    it empty simply forfeits the deduction, and is never stopped.
    """

    @classmethod
    def _details_extra_form_values(cls, post):
        values = super()._details_extra_form_values(post)
        values["social_sec_nr"] = (post.get("social_sec_nr") or "").strip()
        return values

    @classmethod
    def _details_extra_error(cls, values, sponsorship):
        """Refuse a number that is not one of the company's country.

        Nothing else could go into its tax report, whether it is a typo or
        another Nordic country's number. The field stays optional: the
        message says the sponsor may clear it and carry on.
        """
        error = super()._details_extra_error(values, sponsorship)
        if error:
            return error
        ssn = values.get("social_sec_nr")
        if not ssn or not sponsorship._my2_collects_ssn():
            return ""
        country_code = sponsorship._my2_ssn_country_code()
        if sponsorship.env["res.partner"]._my2_normalize_ssn(ssn, country_code):
            return ""
        if country_code == "SE":
            return _(
                "That is not a valid Swedish personnummer. Please check it, or"
                " leave the field empty: we can only report your gift to"
                " Skatteverket with a Swedish personnummer."
            )
        if country_code == "NO":
            return _(
                "That is not a valid Norwegian fødselsnummer or D-nummer."
                " Please check it, or leave the field empty: we can only report"
                " your gift to Skatteetaten with a Norwegian number."
            )
        return _(
            "That is not a valid Danish CPR-nummer. Please check it, or leave"
            " the field empty: we can only report your gift to Skattestyrelsen"
            " with a Danish CPR-nummer."
        )
