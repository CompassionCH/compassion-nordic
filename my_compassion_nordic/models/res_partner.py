from stdnum.dk import cpr
from stdnum.no import fodselsnummer
from stdnum.se import personnummer

from odoo import models

# The validator of each country's national identity number, by country code.
# Only the countries that have a gift report to file are here - see
# SSN_REPORTING_COUNTRIES in res_company.
#
# Finland is absent for the same reason it is absent there. Note that
# compassion_nordic_accounting's own SSN_CONTRY_FMT_LIST lists
# stdnum.fi.veronumero for Finland, which is the construction-industry tax
# number rather than a personal identity code; nothing here depends on it.
SSN_VALIDATORS = {
    "SE": personnummer,
    "NO": fodselsnummer,
    "DK": cpr,
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _my2_check_ssn(self, ssn, country_code):
        """Classify a national identity number typed on the public form.

        Three outcomes, because the form has three things to do with them:

        - ("ok", code): valid for country_code, or - when the company has no
          reporting country of its own - valid for one of the others.
        - ("foreign", code): valid, but for a different Nordic country than
          the one filing the report. A Swede sponsoring on the Norwegian site
          is an ordinary thing to do, and their personnummer is worth keeping
          even though Skatteetaten cannot use it, so this is a notice rather
          than an error.
        - ("invalid", ""): matches no Nordic format at all, which is what a
          typo looks like.

        Never raises, and "empty" is never asked about here: the field is
        optional, so the caller drops an empty value before it gets this far.
        """
        ssn = (ssn or "").strip()
        if not ssn:
            return "invalid", ""
        own = SSN_VALIDATORS.get(country_code)
        if own is not None and own.is_valid(ssn):
            return "ok", country_code
        for code, validator in SSN_VALIDATORS.items():
            if code != country_code and validator.is_valid(ssn):
                # No reporting country of its own (the shared Norden parent
                # company) means nothing to be foreign to.
                return ("foreign" if own is not None else "ok"), code
        return "invalid", ""
