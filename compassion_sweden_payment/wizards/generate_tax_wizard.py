##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import xml.etree.ElementTree as ET
from datetime import datetime

from odoo import _, models
from odoo.exceptions import ValidationError


MIN_AMOUNT = 200  # Minimum amount threshold for Sweden tax reporting (per day)


class GenerateTaxWizard(models.TransientModel):
    _inherit = "generate.tax.wizard"

    def generate_tax(self):
        self._del_old_entry()
        company = self.env.company
        if company.country_id.name != "Sweden":
            return super().generate_tax()
        if not company.company_registry:
            raise ValidationError(_("The Company should have a Tax ID"))

        # Get aggregated amounts with minimum threshold of 200 per day
        # For Sweden, we consider only income greater than kr 200 per day
        grouped_amounts = self._get_paid_invoices_aggregated(
            groupby_fields=["partner_id", "date:day"], min_amount=MIN_AMOUNT
        )

        # Build XML structure for Sweden
        skatteverket = self._build_sweden_xml(company, grouped_amounts)

        # Create and download attachment
        return self._create_and_download_attachment(skatteverket)

    def _build_sweden_xml(self, company, grouped_amounts):
        """Build Sweden-specific XML structure for tax file.

        Args:
            company: Company record
            grouped_amounts: Dictionary of partner_id to amount

        Returns:
            Root XML element
        """
        version = f"{self.xml_version:.1f}"
        skatteverket = ET.Element("Skatteverket")
        skatteverket.attrib = {
            "xmlns": f"http://xmls.skatteverket.se/se/skatteverket/ai/instans/infoForBeskattning/{version}",
            "xmlns:m": f"http://xmls.skatteverket.se/se/skatteverket/ai/gemensamt/infoForBeskattning/{version}",
            "xmlns:ku": f"http://xmls.skatteverket.se/se/skatteverket/ai/komponent/infoForBeskattning/{version}",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "omrade": "Kontrolluppgifter",
            "xsi:schemaLocation": "http://xmls.skatteverket.se/se/skatteverket/ai/instans"
            f"/infoForBeskattning/{version}"
            "http://xmls.skatteverket.se/se/skatteverket/ai"
            f"/kontrolluppgift/instans/Kontrolluppgifter_{version}.xsd",
        }

        # Build Avsandare section
        avsandare = ET.SubElement(skatteverket, "ku:Avsandare")
        orgnr = f"16{company.company_registry.replace('-', '')}"
        self._populate_xml_elements(
            avsandare,
            {"Programnamn": "KUfilsprogrammet", "Organisationsnummer": orgnr},
            tag_prefix="ku:",
        )

        teknisk_kontaktperson = ET.SubElement(avsandare, "ku:TekniskKontaktperson")
        self._populate_xml_elements(
            teknisk_kontaktperson,
            {
                "Namn": company.partner_id.name,
                "Telefon": company.partner_id.phone,
                "Epostadress": company.partner_id.email,
                "Utdelningsadress1": company.partner_id.street,
                "Postnummer": company.partner_id.zip,
                "Postort": company.partner_id.city,
            },
            tag_prefix="ku:",
        )

        self._populate_xml_elements(
            avsandare,
            {"Skapad": f"{datetime.now():%Y-%m-%dT%H:%M:%S}"},
            tag_prefix="ku:",
        )

        # Build Blankettgemensamt section
        blankettgemensamt = ET.SubElement(skatteverket, "ku:Blankettgemensamt")
        uppgiftslamnare = ET.SubElement(blankettgemensamt, "ku:Uppgiftslamnare")
        self._populate_xml_elements(
            uppgiftslamnare, {"UppgiftslamnarePersOrgnr": orgnr}, tag_prefix="ku:"
        )

        kontaktperson = ET.SubElement(uppgiftslamnare, "ku:Kontaktperson")
        self._populate_xml_elements(
            kontaktperson,
            {
                "Namn": company.partner_id.name,
                "Telefon": company.partner_id.phone,
                "Epostadress": company.partner_id.email,
                "Sakomrade": "Skatteverket",
            },
            tag_prefix="ku:",
        )

        # Add partner entries
        for partner_id, amount in grouped_amounts.items():
            if amount < MIN_AMOUNT:
                continue  # Skip amounts below threshold
            partner = self.env["res.partner"].browse(partner_id)
            is_taxable, identifier = self._get_partner_tax_identifier(partner, amount)

            # If the partner is eligible we put it in the file
            if is_taxable:
                blankett = ET.SubElement(skatteverket, "ku:Blankett", nummer="2314")
                arendeinformation = ET.SubElement(blankett, "ku:Arendeinformation")
                self._populate_xml_elements(
                    arendeinformation,
                    {"Arendeagare": orgnr, "Period": str(self.tax_year)},
                    tag_prefix="ku:",
                )

                blankettinnehall = ET.SubElement(blankett, "ku:Blankettinnehall")
                ku65 = ET.SubElement(blankettinnehall, "ku:KU65")

                uppgiftslamnare_ku65 = ET.SubElement(ku65, "ku:UppgiftslamnareKU65")
                self._populate_xml_elements_with_faltkod(
                    uppgiftslamnare_ku65,
                    {
                        "UppgiftslamnarId": (orgnr, "201"),
                        "NamnUppgiftslamnare": (company.name, "202"),
                    },
                )

                self._populate_xml_elements_with_faltkod(
                    ku65,
                    {
                        "Inkomstar": (str(self.tax_year), "203"),
                        "MottagetGavobelopp": (str(int(amount)), "621"),
                        "Specifikationsnummer": (str(partner.ref), "570"),
                    },
                )

                inkomsttagare_ku65 = ET.SubElement(ku65, "ku:InkomsttagareKU65")
                self._populate_xml_elements_with_faltkod(
                    inkomsttagare_ku65,
                    {
                        "Inkomsttagare": (identifier, "215"),
                    },
                )

        return skatteverket

    @staticmethod
    def _populate_xml_elements_with_faltkod(parent, data_map):
        """Populate parent element with child elements that have faltkod attribute.

        Args:
            parent: Parent XML element
            data_map: Dictionary mapping tag names to (value, faltkod) tuples
        """
        for key, (value, faltkod) in data_map.items():
            elem = ET.SubElement(parent, f"ku:{key}", {"faltkod": faltkod})
            elem.text = value
