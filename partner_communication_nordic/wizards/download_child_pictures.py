##############################################################################
#
#    Copyright (C) 2016-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import logging
from io import BytesIO
from zipfile import ZipFile

from pdf2image import convert_from_bytes

from odoo import api, fields, models
from odoo.tools.image import image_data_uri

logger = logging.getLogger(__name__)


class DownloadChildPictures(models.TransientModel):
    _inherit = "child.pictures.download.wizard"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    type = fields.Selection(
        selection_add=[("biennial", "Biennial Photo")], ondelete={"biennial": "cascade"}
    )

    ##########################################################################
    #                             VIEW CALLBACKS                             #
    ##########################################################################
    def get_pictures(self):
        """Create the zip archive from the selected letters."""
        if self.type == "biennial":
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, "w") as zip_data:
                children = self.child_ids.filtered("portrait")
                found = len(children)
                for i, image in enumerate(
                    convert_from_bytes(
                        self.env["ir.actions.report"]._render_qweb_pdf(
                            "child_compassion.report_child_picture", children.ids
                        )[0]
                    )
                ):
                    buffer = BytesIO()
                    image.save(buffer, format="JPEG", quality=100)
                    zip_data.writestr(f"{children[i].local_id}.jpg", buffer.getvalue())
            zip_buffer.seek(0)
            if found:
                self.download_data = base64.b64encode(zip_buffer.read())
            self.information = f"Zip file contains {found} pictures.\n\n"
            return {
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_id": self.id,
                "res_model": self._name,
                "context": self.env.context,
                "target": "new",
            }
        else:
            return super().get_pictures()

    @api.depends("type")
    def _compute_preview(self):
        if self.type == "biennial":
            child = self.child_ids.filtered("portrait")[:1]
            if child:
                image = convert_from_bytes(
                    self.env["ir.actions.report"]._render_qweb_pdf(
                        "child_compassion.report_child_picture", child.ids
                    )[0]
                )[0]
                image = image.resize((image.width // 2, image.height // 2))
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=70)
                self.preview = image_data_uri(base64.b64encode(buffer.getvalue()))
            else:
                self.preview = False
        else:
            super()._compute_preview()
