##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import csv
from functools import reduce
from itertools import groupby
from odoo import api, models, fields
import io
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom


class GenerateTaxWizard(models.Model):
    _name = "generate.tax.wizard"
    _description = "Generate Tax files"

    year = fields.Char("Fiscal Year", default=str(datetime.now().year - 1))
    xml_version = fields.Float("XML version", default=8)

    def generate_tax(self):
        pass
