from odoo import _

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)


class MyCompassionNewSponsorshipNordic(MyCompassionNewSponsorshipController):
    """The Nordic entities ask one more thing on the post-payment details
    form: the sponsor's national identity number, which is what lets the
    gift be reported to their tax authority so they get their deduction.

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
        """Reject only what is not a national identity number at all.

        A number belonging to another Nordic country is stored as it is: a
        Swede sponsoring on the Norwegian site is ordinary, and losing their
        personnummer over it would help nobody. Only a value matching no
        Nordic format is refused, because that is what a typo looks like -
        and even then the sponsor can clear the optional field and carry on.
        """
        error = super()._details_extra_error(values, sponsorship)
        if error:
            return error
        ssn = (values.get("social_sec_nr") or "").strip()
        if not ssn or not sponsorship._my2_collects_ssn():
            return ""
        outcome, _code = sponsorship.env["res.partner"]._my2_check_ssn(
            ssn, sponsorship._my2_ssn_country_code()
        )
        if outcome == "invalid":
            return _(
                "That does not look like a valid national identity number."
                " Please check it, or leave the field empty - it is optional."
            )
        return ""
