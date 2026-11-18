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

from stdnum.se import orgnr as se_orgnr
from stdnum.se import personnummer
from stdnum.se import vat as se_vat

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

# Skatteverket reporting thresholds (KU65). An occasion is one day: all the
# donor's income lines of that day are added up before the threshold applies.
INDIVIDUAL_MIN_PER_OCCASION = 200
INDIVIDUAL_MIN_PER_YEAR = 2000
# Smaller company gifts never add up to it.
COMPANY_MIN_PER_OCCASION = 2000
# Company gifts give a tax reduction (and are reported) from this income year.
COMPANY_FIRST_INCOME_YEAR = 2026


class GenerateTaxWizard(models.TransientModel):
    _inherit = "generate.tax.wizard"

    se_donor_type = fields.Selection(
        [("individual", "Individuals"), ("company", "Companies")],
        string="Donors",
        default="individual",
        required=True,
        help="Skatteverket accepts both in one file; they are generated "
        "separately to check and send them independently.",
    )

    def generate_tax(self):
        self._del_old_entry()
        company = self.env.company
        if company.country_id.name != "Sweden":
            return super().generate_tax()
        if not company.company_registry:
            raise ValidationError(_("The Company should have a Tax ID"))

        if self.se_donor_type == "company":
            if int(self.tax_year) < COMPANY_FIRST_INCOME_YEAR:
                raise UserError(
                    _(
                        "Company gifts are reported from income year %s.",
                        COMPANY_FIRST_INCOME_YEAR,
                    )
                )
            grouped_amounts = self._get_paid_invoices_aggregated(
                groupby_fields=["partner_id", "date:day"],
                min_amount=COMPANY_MIN_PER_OCCASION,
            )
            filename_prefix = "Tax_companies"
        else:
            grouped_amounts = {
                partner_id: amount
                for partner_id, amount in self._get_paid_invoices_aggregated(
                    groupby_fields=["partner_id", "date:day"],
                    min_amount=INDIVIDUAL_MIN_PER_OCCASION,
                ).items()
                if amount >= INDIVIDUAL_MIN_PER_YEAR
            }
            filename_prefix = "Tax"

        skatteverket = self._build_sweden_xml(company, grouped_amounts)
        return self._create_and_download_attachment(skatteverket, filename_prefix)

    def _del_old_entry(self):
        # Keep the results of the other donor type's file
        if self.env.company.country_id.code != "SE":
            return super()._del_old_entry()
        self.env["res.partner.tax.file.result"].with_context(active_test=False).search(
            [
                ("tax_company_id", "=", self.env.company.id),
                ("partner_id.is_company", "=", self.se_donor_type == "company"),
            ]
        ).sudo().unlink()

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
            if amount <= 0:
                continue
            partner = self.env["res.partner"].browse(partner_id)
            identifier = self._se_tax_identifier(partner, amount)

            # If the partner is eligible we put it in the file
            if identifier:
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

    def _se_tax_identifier(self, partner, amount):
        """Field 215 of the donor matching the selected donor type, logging
        why a donor is left out.

        :return: the identifier, or None when the donor is not reported
        """
        if self.se_donor_type == "company":
            if not partner.is_company:
                return None
            identifier = self._se_orgnr_identifier(partner.vat)
            if not partner.vat:
                state = "empty_vat"
            else:
                state = "valid" if identifier else "invalid_vat"
            self._log_tax_file_result(partner, amount, state)
            return identifier

        if partner.is_company:
            return None
        ssn = partner.social_sec_nr
        identifier = self._se_personnummer_identifier(ssn)
        if not ssn:
            state = "empty_ssn"
        elif not identifier:
            state = "invalid_ssn"
        elif int(self.tax_year) - personnummer.get_birth_date(ssn).year < 18:
            state = "under_18"
            identifier = None
        else:
            state = "valid"
        self._log_tax_file_result(partner, amount, state)
        return identifier

    @staticmethod
    def _se_personnummer_identifier(ssn):
        """YYYYMMDDNNNN: Skatteverket requires the century, which a
        YYMMDD-NNNN number only gives through its separator."""
        if not ssn or not personnummer.is_valid(ssn):
            return None
        digits = "".join(char for char in ssn if char.isdigit())
        return f"{personnummer.get_birth_date(ssn).year // 100}{digits[-10:]}"

    @classmethod
    def _se_orgnr_identifier(cls, vat):
        """16 followed by the 10-digit organisation number (an SE VAT number is
        accepted too). A sole trader's organisation number is its owner's
        personnummer, reported as such."""
        if not vat:
            return None
        if se_vat.is_valid(vat):
            number = se_vat.compact(vat)[:10]
        elif se_orgnr.is_valid(vat):
            number = se_orgnr.compact(vat)
        else:
            return None
        if number[2] in "01":  # month of a personnummer, not an organisation
            return cls._se_personnummer_identifier(number)
        return f"16{number}"

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
