from stdnum.dk import cpr
from stdnum.no import fodselsnummer
from stdnum.se import personnummer

from odoo import api, models


def _swedish_personnummer(number):
    """YYYYMMDD-NNNN, the form Skatteverket's KU65 wants once the dash is
    dropped (twelve digits). A ten-digit number gets its century from the
    birth date stdnum reads in it, which honours the "+" of a centenarian."""
    digits = personnummer.compact(number).replace("-", "").replace("+", "")
    if len(digits) == 10:
        century = personnummer.get_birth_date(number).year // 100
        digits = f"{century}{digits}"
    return f"{digits[:8]}-{digits[8:]}"


# The national identity number of each country whose tax authority receives
# a gift report, keyed by country code: (validator, normaliser). Only the
# countries listed in SSN_REPORTING_COUNTRIES (res_company) belong here.
#
# The normalised forms are the ones already on file for each country, which
# the tax exports read: SE twelve digits with a dash, NO eleven digits, DK
# ten digits. A Danish CPR-nummer has no checksum since 2007, so its
# validation is only length and a plausible birth date.
SSN_FORMATS = {
    "SE": (personnummer, _swedish_personnummer),
    "NO": (fodselsnummer, fodselsnummer.compact),
    "DK": (cpr, cpr.compact),
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _my2_normalize_ssn(self, ssn, country_code):
        """A national identity number typed on the public details form, in
        the form country_code's tax report uses, or "" when it is not a
        valid number of that country.

        Only the reporting country's own format is accepted. A Swede's
        personnummer typed on the Norwegian site could never go into
        Skatteetaten's report, and the tax exports do not check which
        country a stored number belongs to.
        """
        ssn = (ssn or "").strip()
        validator, normalize = SSN_FORMATS.get(country_code, (None, None))
        if not ssn or validator is None or not validator.is_valid(ssn):
            return ""
        return normalize(ssn)
