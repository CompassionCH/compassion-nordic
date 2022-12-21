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

# Library for sweden, norway, denmark, finland
SSN_CONTRY_FMT_LIST = [personnummer, fodselsnummer, cpr, veronumero]
VAT_COUNTRY_FMT_LIST = [se_org, no_org, cvr, alv]


class ResPartner(models.Model):
    _inherit = "res.partner"

    social_sec_nr = fields.Char(string="Social security number")
    _country_id = False

    @api.depends('social_sec_nr')
    @api.constrains("social_sec_nr")
    def _compute_sec_nr(self):
        for partner in self:
            if partner.social_sec_nr:
                # If a social security number has been filled in we check the format
                # Then we extract informations from it if it's possible
                # (certain formats have no informations)
                is_valid, valid_fmt = self._validate_ssn()
                if is_valid:
                    if valid_fmt in self._list_has_bday():
                        if valid_fmt in del_from_lib(SSN_CONTRY_FMT_LIST, [veronumero, cpr]):
                            partner.gender = valid_fmt.get_gender(self.social_sec_nr)
                        partner.birthdate_date = valid_fmt.get_birth_date(self.social_sec_nr)
                        partner._compute_age()
                else:
                    raise UserError(ERROR_MESSAGE.format(err_msg="Not a valid social security number."))

    def _validate_ssn(self):
        self.ensure_one()
        for ssn_country_fmt in SSN_CONTRY_FMT_LIST:
            if ssn_country_fmt.is_valid(self.social_sec_nr):
                return True, ssn_country_fmt
        return False, False

    def _validate_vat(self):
        self.ensure_one()
        for vat_country_fmt in VAT_COUNTRY_FMT_LIST:
            if vat_country_fmt.is_valid(self.vat):
                return True, vat_country_fmt
        return False, False

    @staticmethod
    def _list_has_bday():
        return del_from_lib(SSN_CONTRY_FMT_LIST, [veronumero])

def del_from_lib(orig_lib_list, lib_list):
    return [fmt for fmt in orig_lib_list if fmt not in lib_list]
