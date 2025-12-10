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
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom import minidom

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GenerateTaxWizard(models.TransientModel):
    _name = "generate.tax.wizard"
    _description = "Generate Tax files"

    tax_year = fields.Selection(
        "_year_selection",
        "Calendar Year",
        default=str(datetime.today().year - 1),
        required=True,
    )
    xml_version = fields.Float("XML version", default=8)
    is_sweden = fields.Boolean(
        default=lambda s: s.env.company.country_id == s.env.ref("base.se")
    )

    _sql_constraints = [
        (
            "tax_year_not_in_the_future",
            "CHECK(tax_year < EXTRACT(year FROM CURRENT_DATE))",
            "Year of taxation can't be in the future",
        ),
    ]

    @api.model
    def _year_selection(self):
        curr_year = datetime.today().year
        year_list = []
        # We give 8 year because the legislation
        # ask for 7 years archive in the nordics countries
        while curr_year >= datetime.today().year - 8:
            year_list.append((str(curr_year), str(curr_year)))
            curr_year -= 1
        return year_list

    def generate_tax(self):
        try:
            raise NotImplementedError()
        except NotImplementedError as err:
            raise UserError(
                _("The company that you are on doesn't support this feature.")
            ) from err

    # Common helper methods for XML generation
    @staticmethod
    def _create_xml_element(parent, tag, text=None, **attributes):
        """Create an XML element with optional text content and attributes.

        Args:
            parent: Parent XML element
            tag: Tag name for the new element
            text: Optional text content
            **attributes: Optional XML attributes

        Returns:
            The created XML element
        """
        elem = ET.SubElement(parent, tag, attributes)
        if text is not None:
            elem.text = text
        return elem

    @staticmethod
    def _populate_xml_elements(parent, data_map, tag_prefix=""):
        """Populate parent element with child elements from a data map.

        Args:
            parent: Parent XML element
            data_map: Dictionary mapping tag names to text values
            tag_prefix: Optional prefix to add to all tag names
        """
        for key, value in data_map.items():
            tag = f"{tag_prefix}{key}" if tag_prefix else key
            GenerateTaxWizard._create_xml_element(parent, tag, value)

    def _get_paid_invoices_aggregated(self, groupby_fields, min_amount=0):
        """Get aggregated amounts from paid invoices for the tax year.

        Args:
            groupby_fields: List of fields to group by (e.g., ["partner_id"])
            min_amount: Minimum amount threshold to include in results

        Returns:
            Dictionary mapping partner_id to total amount
        """
        company = self.env.company
        ret = self.env["account.move"].read_group(
            [
                ("payment_state", "=", "paid"),
                ("company_id", "=", company.id),
                ("last_payment", ">=", datetime(int(self.tax_year), 1, 1)),
                ("last_payment", "<=", datetime(int(self.tax_year), 12, 31)),
                ("invoice_category", "!=", "other"),
            ],
            ["amount_total", "last_payment"],
            groupby=groupby_fields,
            lazy=False,
        )

        # Aggregate amounts by partner
        total_amount_year = {}
        for record in ret:
            partner_id = record["partner_id"][0]
            if partner_id not in total_amount_year:
                total_amount_year[partner_id] = 0
            total_amount_year[partner_id] += record["amount_total"]

        # Filter by minimum amount if specified
        if min_amount > 0:
            return {
                partner_id: amount
                for partner_id, amount in total_amount_year.items()
                if amount >= min_amount
            }
        return total_amount_year

    def _create_and_download_attachment(self, xml_element, filename_prefix="Tax"):
        """Create an attachment from XML and return download action.

        Args:
            xml_element: Root XML element to convert to file
            filename_prefix: Prefix for the filename (default: "Tax")

        Returns:
            Action dictionary for downloading the file
        """
        company = self.env.company
        xml_str = minidom.parseString(ET.tostring(xml_element)).toprettyxml(
            indent="   ", encoding="UTF-8"
        )

        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        attachment_obj = self.env["ir.attachment"]

        # Create attachment
        data = base64.b64encode(xml_str)
        attachment_id = attachment_obj.create(
            [{"name": f"{filename_prefix}_{self.tax_year}_{company.name}.xml", "datas": data}]
        )

        # Prepare download URL
        download_url = f"/web/content/{attachment_id.id}?download=true"

        # Return download action
        return {
            "type": "ir.actions.act_url",
            "url": f"{base_url}{download_url}",
            "target": "new",
        }

    def _validate_vat_company(self, partner, amount):
        """Log the company in the model used for result of tax generation
        Some company may have a bad VAT number format or an empty one we log the detail

        @return we return a boolean that define if a company is eligible or not
        """
        state = "valid"
        is_valid, valid_fmt = partner._validate_vat()
        if not partner.vat:
            state = "empty_vat"
        elif not is_valid:
            state = "invalid_vat"
        # Log the entry in the model made for this
        self.env["res.partner.tax.file.result"].create(
            {
                "partner_id": partner.id,
                "tax_company_id": self.env.company.id,
                "tax_year": self.tax_year,
                "yearly_amount": amount,
                "state": state,
            }
        )

        if state in ["empty_vat", "invalid_vat"]:
            return False
        return True

    def _validate_partner_tax_eligibility(self, partner, amount):
        """Log the partner in the model used for result of tax generation
        Some partner may have a bad SSN format or an empty one we log the detail

        @return we return a boolean that define if a partner is eligible or not
        """
        state = "valid"
        is_valid, valid_fmt = partner._validate_ssn()
        if not partner.social_sec_nr:
            state = "empty_ssn"
        elif not is_valid:
            state = "invalid_ssn"
        elif valid_fmt in partner._list_has_bday():
            if (
                0
                < datetime.strptime(f"{self.tax_year}-12-31", "%Y-%m-%d").year
                - valid_fmt.get_birth_date(partner.social_sec_nr).year
                < 18
            ):
                state = "under_18"
        # Log the entry in the model made for this
        self.env["res.partner.tax.file.result"].create(
            {
                "partner_id": partner.id,
                "tax_company_id": self.env.company.id,
                "tax_year": self.tax_year,
                "yearly_amount": amount,
                "state": state,
            }
        )

        if state in ["invalid_ssn", "under_18", "empty_ssn"]:
            return False
        return True

    def _del_old_entry(self):
        to_del = self.env["res.partner.tax.file.result"].search(
            [("tax_company_id", "=", self.env.company.id)]
        )
        to_del.sudo().unlink()
