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

from stdnum.exceptions import InvalidLength, InvalidFormat, InvalidChecksum, InvalidComponent
from stdnum.no import fodselsnummer
from stdnum.se import personnummer

from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    social_sec_nr = fields.Char(string="Social security number")
    _country_id = False
    # TODO implement ref_social_sec_nr to activate that constaints again
    # _sql_constraints = [
    #     ('social_sec_nr_unique',
    #      'UNIQUE(social_sec_nr)',
    #      'social security number field needs to be unique'
    #      )
    # ]

    def _is_swedish(self, partner_country_id):
        return partner_country_id == self.env.ref("base.se")

    def _is_norwegian(self, partner_country_id):
        return partner_country_id == self.env.ref("base.no")

    @api.depends('social_sec_nr')
    @api.constrains("social_sec_nr")
    def calculate_age(self):
        for partner in self:
            partner_country = partner.country_id
            # If a social security number has been filled in we check the format
            # Then we extract gender bday from it
            # The format for swedish and norwegian one aren't the same
            if self._is_swedish(partner_country):
                social_sec = partner.social_sec_nr
                if social_sec:
                    self._validate_sec_nr(partner.country_id, social_sec)
                    partner.gender = personnummer.get_gender(social_sec)
                    partner.birthdate_date = personnummer.get_birth_date(social_sec)
                    partner._compute_age()
            elif self._is_norwegian(partner_country):
                social_sec = partner.social_sec_nr
                if social_sec:
                    self._validate_sec_nr(partner.country_id, social_sec)
                    partner.gender = fodselsnummer.get_gender(social_sec)
                    partner.birthdate_date = fodselsnummer.get_birth_date(social_sec)
                    partner._compute_age()


    def _validate_sec_nr(self, country, social_sec):
        ERROR_MESSAGE = "SSN (Social Security Number): {err_msg}"
        try:
            if self._is_swedish(country):
                personnummer.validate(social_sec)
            elif self._is_norwegian(country):
                fodselsnummer.validate(social_sec)
        except InvalidLength as e:
            raise UserError(ERROR_MESSAGE.format(err_msg=e.message))
        except InvalidFormat as e:
            raise UserError(ERROR_MESSAGE.format(err_msg=e.message))
        except InvalidChecksum as e:
            raise UserError(ERROR_MESSAGE.format(err_msg=e.message))
        except InvalidComponent as e:
            raise UserError(ERROR_MESSAGE.format(err_msg="The birthdate can not be in the future"))