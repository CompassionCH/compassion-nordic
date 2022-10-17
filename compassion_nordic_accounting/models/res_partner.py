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

from odoo import models, api, _, fields
from datetime import date
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    _patterns = re.compile(
        r'(?P<day>\d{2})(?P<month>\d{2})(?P<year>\d{2})(?P<century_code>\d{1})'
        r'(?P<i2>\d{1})(?P<gender>\d{1})(?P<checksum1>\d{1})(?P<checksum2>\d{1})'
    )
    _checksum1_coefficient = [3, 7, 6, 1, 8, 9, 4, 5, 2, 1]
    _checksum2_coefficient = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 1]

    age = fields.Char(string="Age", )  # compute="calculate_age" removed computed
    social_sec_nr = fields.Char(string="Social security number")

    _sql_constraints = [
        ('social_sec_nr_unique',
         'UNIQUE(social_sec_nr)',
         'social security number field needs to be unique'
         )]

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
            if rec.country_id == self.env.ref("base.se"):
                today = date.today()
                social_sec = rec.social_sec_nr
                social_sec_stripped = ""
                if social_sec:
                    if re.fullmatch("([0-9]){8}-([0-9]){4}", social_sec):
                        social_sec_stripped = social_sec.split("-")[0]
                    elif re.fullmatch("([0-9]){12}", social_sec):
                        social_sec_stripped = social_sec[:8]
                        rec.social_sec_nr = "%s-%s" % (
                            social_sec_stripped,
                            social_sec[8:12],
                        )
                    elif re.fullmatch("([0-9]){6}-([0-9]){4}", social_sec):
                        social_sec_stripped = social_sec.split("-")[0]
                        error_message = _(
                            "Social security number %s is formated as YYMMDD-NNNN, this format is not accepted"
                        ) % social_sec
                        self._raise_error(error_message)
                    elif re.fullmatch("([0-9]){10}", social_sec):
                        social_sec_stripped = social_sec[:8]
                        rec.social_sec_nr = "%s-%s" % (
                            social_sec_stripped,
                            social_sec[8:12],
                        )
                        error_message = _(
                            "Social security number %s is frmated as YYMMDDNNNN, this format is not accepted"
                        ) % social_sec
                        self._raise_error(error_message)
                    else:
                        error_message = _(
                            "Social security number %s is not correctly formated."
                        ) % social_sec
                        self._raise_error(error_message)
                    rec.birthdate_date = date(1980, 1, 1)
                    rec.gender = 'F' if int(social_sec_stripped[-1]) % 2 == 0 else 'M'
                    if len(social_sec_stripped) == 6:
                        yr = social_sec_stripped[:2]
                        year = int("20" + yr)
                        month = int(social_sec_stripped[2:4])
                        day = int(social_sec_stripped[4:6])
                        if day > 60:
                            day = day - 60
                        try:
                            rec.birthdate_date = date(year, month, day)
                            rec._compute_age()
                        except:
                            error_message = _(
                                "Could not convert social security number %s to date"
                            ) % social_sec
                            self._raise_error(error_message)
                        # if social security numbers with 10 numbers are reallowed,
                        # change this to something more reasonable in case children
                        # are allowed to register
                        if today.year - rec.birthdate_date.year < 18:
                            year = int("19" + yr)
                            try:
                                rec.birthdate_date = date(year, month, day)
                                rec._compute_age()
                            except:
                                error_message = _(
                                    "Could not convert social security number %s to date"
                                ) % social_sec_stripped
                                self._raise_error(error_message)
                    elif len(social_sec_stripped) == 8:
                        year = int(social_sec_stripped[:4])
                        month = int(social_sec_stripped[4:6])
                        day = int(social_sec_stripped[6:8])

                        if day > 60:
                            day = day - 60
                        try:
                            rec.birthdate_date = date(year, month, day)
                            rec._compute_age()
                        except:
                            error_message = _(
                                "Could not convert social security number %s to date"
                            ) % social_sec_stripped
                            self._raise_error(error_message)

                    else:
                        error_message = _(
                            "Incorrectly formated social security number %s"
                        ) % social_sec
                        self._raise_error(error_message)
            elif rec.country_id == self.env.ref("base.no"):
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
                    rec.gender = 'F' if gender_code % 2 == 0 else 'M'
                    if not self.checksum(sec_num[:10], self._checksum1_coefficient):
                        self._raise_error("Invalid checksum 1")
                    if not self.checksum(sec_num, self._checksum2_coefficient):
                        self._raise_error("Invalid checksum 2")
                    rec.birthdate_date = date(year, month, day)
                    rec._compute_age()
