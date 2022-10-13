##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from functools import reduce

from odoo import models, fields, api, _
from datetime import date
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    age = fields.Char(string="Age", )  # compute="calculate_age" removed computed
    social_sec_nr = fields.Char(string="Social security number")
    social_sec_nr_age = fields.Char(string="Social security number", compute="combine_social_sec_nr_age")
    _patterns = re.compile(
        r'(?P<day>\d{2})(?P<month>\d{2})(?P<year>\d{2})(?P<century_code>\d{1})'
        r'(?P<i2>\d{1})(?P<gender>\d{1})(?P<checksum1>\d{1})(?P<checksum2>\d{1})'
    )
    _checksum1_coefficient = [3, 7, 6, 1, 8, 9, 4, 5, 2, 1]
    _checksum2_coefficient = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 1]

    @staticmethod
    def checksum(value, coefficient):
        return (reduce(lambda a, b: a + (int(b[0]) * b[1]), zip(value, coefficient), 0)) % 11 == 0

    def _raise_error(self, error):
        raise ValidationError(
            _(
                "Please input a correctly formatted social security number.\nThe correct format is "
                "DDMMYYIIICC: %s\n ", error
            )
        )

    def compute_year(self, year_code, century_code):
        century = 19
        if 0 <= century_code < 5:
            if year_code < 40:
                century = 20
        elif century_code < 8:
            century = 20 if year_code < 55 else 18
        elif century_code < 9:
            century = 20
        else:
            if year_code < 40:
                self._raise_error("Wrong Century code")
            elif year_code < 55:
                # This part may be wrong
                century = 20
        return (century * 100) + year_code

    @api.depends('social_sec_nr')
    @api.constrains("social_sec_nr")
    def calculate_age(self):
        for rec in self:
            if rec.country_id.name == "Sweden":
                super().calculate_age()
            elif rec.country_id.name == "Norway":
                sec_num = rec.social_sec_nr
                if sec_num:
                    if len(sec_num) != 11:
                        self._raise_error("Size should be equal to 11")
                    group_matches = self._patterns.match(sec_num).groupdict()
                    day = int(group_matches['day'])
                    if day < 1 or day > 31:
                        self._raise_error("Day should be between 1 and 31")
                    month = int(group_matches['month'])
                    if month < 1 or month > 12:
                        self._raise_error("Month should be between 1 and 12")
                    year = self.compute_year(int(group_matches['year']), int(group_matches['century_code']))
                    gender_code = int(group_matches['gender'])
                    self.gender = 'female' if gender_code % 2 == 0 else 'male'
                    if not self.checksum(sec_num[:10], self._checksum1_coefficient):
                        self._raise_error("Invalid checksum 1")
                    if not self.checksum(sec_num, self._checksum2_coefficient):
                        self._raise_error("Invalid checksum 2")
                    self.birthdate_date = date(year, month, day)
                    self._compute_age()
