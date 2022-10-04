##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import csv

from odoo import api, models, fields
import io


class LoadMandateWizard(models.Model):
    _name = "load.mandate.wizard"
    _description = "Link gifts with letters"

    data_mandate = fields.Binary("Mandate file")
    name_file = fields.Char("File Name")

    def generate_new_mandate(self):
        pass
