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

from odoo import models


class GenerateTaxWizard(models.TransientModel):
    _inherit = "generate.tax.wizard"

    def generate_tax(self):
        self._del_old_entry()
        company = self.env.company
        if company.country_id.name != "Norway":
            return super().generate_tax()

        # Get aggregated amounts with minimum threshold of 500 per year
        # For Norway, we consider only total income greater than kr 500 per year
        grouped_amounts = self._get_paid_invoices_aggregated(
            groupby_fields=["partner_id"], min_amount=500
        )

        # Build XML structure for Norway
        melding = self._build_norway_xml(company, grouped_amounts)

        # Create and download attachment
        return self._create_and_download_attachment(melding)

    def _build_norway_xml(self, company, grouped_amounts):
        """Build Norway-specific XML structure for tax file.

        Args:
            company: Company record
            grouped_amounts: Dictionary of partner_id to amount

        Returns:
            Root XML element
        """
        melding = ET.Element("melding")
        melding.attrib = {
            "xmlns": "urn:ske:fastsetting:innsamling:gavefrivilligorganisasjon:v2",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            " xsi:schemaLocation": "urn:ske:fastsetting:innsamling:"
            "gavefrivilligorganisasjon:v2 "
            "gavefrivilligorganisasjon_v2_0.xsd ",
        }

        leveranse = ET.SubElement(melding, "leveranse")
        kildesystem = ET.SubElement(leveranse, "kildesystem")
        kildesystem.text = "Kildesystemet v2.0.5"

        oppgavegiver = ET.SubElement(leveranse, "oppgavegiver")
        self._populate_xml_elements(
            oppgavegiver,
            {
                "organisasjonsnummer": company.company_registry.replace(" ", ""),
                "organisasjonsnavn": company.name,
            },
        )

        kontaktinformasjon = ET.SubElement(oppgavegiver, "kontaktinformasjon")
        self._populate_xml_elements(
            kontaktinformasjon,
            {
                "navn": company.partner_id.name,
                "telefonnummer": company.partner_id.phone,
                "varselEpostadresse": company.partner_id.email,
            },
        )

        self._populate_xml_elements(
            leveranse,
            {
                "inntektsaar": str(self.tax_year),
                "oppgavegiversLeveranseReferanse": f"REF{self.tax_year}"
                f"{datetime.now():%d%m%Y}",
                "leveransetype": "ordinaer",
            },
        )

        total_amount = 0
        total_partner = 0

        for partner_id, amount in grouped_amounts.items():
            partner = self.env["res.partner"].browse(partner_id)
            is_taxable, identifier = self._get_partner_tax_identifier(partner, amount)

            # If the partner is eligible we put it in the file
            if is_taxable:
                oppgave = ET.SubElement(leveranse, "oppgave")
                oppgaveeier = ET.SubElement(oppgave, "oppgaveeier")
                self._populate_xml_elements(
                    oppgaveeier,
                    {"foedselsnummer": str(identifier), "navn": partner.name},
                )
                self._populate_xml_elements(oppgave, {"beloep": str(int(amount))})
                total_amount += amount
                total_partner += 1

        oppgaveoppsummering = ET.SubElement(leveranse, "oppgaveoppsummering")
        self._populate_xml_elements(
            oppgaveoppsummering,
            {"antallOppgaver": str(total_partner), "sumBeloep": str(int(total_amount))},
        )

        return melding

    def _get_partner_tax_identifier(self, partner, amount):
        """Get tax identifier for partner based on validation.

        Args:
            partner: Partner record
            amount: Transaction amount

        Returns:
            Tuple of (is_taxable, identifier)
        """
        is_taxable = False
        identifier = None

        # We test the tax identifier to make sure it is valid
        if (not partner.is_company) and self._validate_partner_tax_eligibility(
            partner, amount
        ):
            is_taxable = True
            identifier = partner.social_sec_nr
        elif partner.is_company and self._validate_vat_company(partner, amount):
            is_taxable = True
            identifier = partner.vat

        return is_taxable, identifier
