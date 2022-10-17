##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from . import controllers
from . import wizards

from odoo.addons.message_center_compassion.tools.load_mappings import \
    load_mapping_files


def load_mappings(cr, registry):
    path = "wordpress_api/static/mappings/"
    files = ["child.json"]
    load_mapping_files(cr, path, files)
