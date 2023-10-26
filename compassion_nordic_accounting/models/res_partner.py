##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from stdnum.se import personnummer, orgnr as se_org
from stdnum.no import fodselsnummer, orgnr as no_org
from stdnum.dk import cpr, cvr
from stdnum.fi import veronumero, alv

from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
ERROR_MESSAGE = "SSN (Social Security Number): {err_msg}"

# SSN and VAT format we accept for sweden, norway, denmark and finland
SSN_CONTRY_FMT_LIST = [personnummer, fodselsnummer, cpr, veronumero]
VAT_COUNTRY_FMT_LIST = [se_org, no_org, cvr, alv]


class ResPartner(models.Model):
    _inherit = "res.partner"

    social_sec_nr = fields.Char(string="Social security number")
    _country_id = False

    @api.depends("social_sec_nr")
    def _compute_sec_nr(self):
        """Fill the value of the age, gender and birth_day if we're able to calculate it from SSN"""
        for partner in self:
            if partner.social_sec_nr:
                # If a social security number has been filled in we check the format
                # Then we extract informations from it if it's possible
                # (certain formats have no informations)
                is_valid, valid_fmt = self._validate_ssn()
                if is_valid:
                    if valid_fmt in self._list_has_bday():
                        if valid_fmt in del_from_lib(
                            SSN_CONTRY_FMT_LIST, [veronumero, cpr]
                        ):
                            partner.gender = valid_fmt.get_gender(self.social_sec_nr)
                        partner.birthdate_date = valid_fmt.get_birth_date(
                            self.social_sec_nr
                        )
                        partner._compute_age()

    @api.constrains("social_sec_nr")
    def _constrains_ssn(self):
        """Validate that the SSN format is the good one. If it's not the case raise an exception to the user."""
        for partner in self:
            if partner.social_sec_nr:
                if not self._validate_ssn():
                    raise UserError(
                        ERROR_MESSAGE.format(
                            err_msg="Not a valid social security number."
                        )
                    )

    def _validate_ssn(self):
        """Function to validate that the SSN format is one accepted by our system

        @return is_valid Boolean, a stdnum object that define the good SSN fmt
        """
        self.ensure_one()
        # Loop on the format we accept
        for ssn_country_fmt in SSN_CONTRY_FMT_LIST:
            # if the SSN is valid in one of the format we return the format
            if ssn_country_fmt.is_valid(self.social_sec_nr):
                return True, ssn_country_fmt
        return False, False

    def _validate_vat(self):
        """Function to validate that the VAT format is one accepted by our system.
        in some case it actually isn't VAT but it's organisation number.

        @return is_valid Boolean, a stdnum object that define the good VAT fmt
        """
        self.ensure_one()
        # Loop on the format we accept
        for vat_country_fmt in VAT_COUNTRY_FMT_LIST:
            # if the vat format is matching one of the accepted one we return the lib
            if vat_country_fmt.is_valid(self.vat):
                return True, vat_country_fmt
        return False, False

    @staticmethod
    def _list_has_bday():
        """Function that return the library objects that have the get_birth_date() function

        @return list of stdnum library object
        """
        return del_from_lib(SSN_CONTRY_FMT_LIST, [veronumero])

    def anonymize(self, vals=None):
        mandates = self.env["account.banking.mandate"].search(
            [("partner_id", "=", self.id)]
        )
        account_moves = self.env["account.move"].search(
            [
                ("mandate_id", "in", mandates.ids),
            ]
        )
        account_moves.write({"mandate_id": False})
        # Delete records from account_banking_mandate
        mandates.with_context(tracking_disable=True).unlink()
        self.with_context(no_upsert=True, tracking_disable=True).write(
            {
                "social_sec_nr": False,
            }
        )
        return super().anonymize(vals)


def del_from_lib(orig_lib_list, lib_list):
    """@return a new list of stdnum object library"""
    return [fmt for fmt in orig_lib_list if fmt not in lib_list]
