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

from odoo import models
from odoo.exceptions import ValidationError


class GenerateTaxWizard(models.TransientModel):
    _inherit = "generate.tax.wizard"

    def generate_tax(self):
        self._del_old_entry()
        company = self.env.company
        if company.country_id.name != "Sweden":
            return super().generate_tax()
        if not company.company_registry:
            raise ValidationError(f"The Company should have a Tax ID")
        ret = self.env['account.move'].read_group([
            ('payment_state', '=', 'paid'),
            ('company_id', '=', company.id),
            ('last_payment', '>=', datetime(int(self.tax_year), 1, 1)),
            ('last_payment', '<=', datetime(int(self.tax_year), 12, 31)),
        ], ['amount_total', 'last_payment'],
            groupby=['partner_id', 'last_payment:day'], lazy=False)
        total_amount_year = {}
        for a in ret:
            if a['amount_total'] >= 200:
                if a['partner_id'][0] not in total_amount_year:
                    total_amount_year[a['partner_id'][0]] = 0
                total_amount_year[a['partner_id'][0]] += a['amount_total']

        def sub_with_txt(parent, tag, text, **extra):
            elem = ET.SubElement(parent, tag, extra)
            elem.text = text
            return elem

        def text_map_faltkod(parent, data_map: dict):
            for key, (value, faltkod) in data_map.items():
                sub_with_txt(parent, f"ku:{key}", value, faltkod=faltkod)

        def text_map(parent, data_map: dict):
            for key, value in data_map.items():
                sub_with_txt(parent, f"ku:{key}", value)
        version = f"{self.xml_version:.1f}"
        Skatteverket = ET.Element('Skatteverket')
        Skatteverket.attrib = {"xmlns": f"http://xmls.skatteverket.se/se/skatteverket/ai/instans/infoForBeskattning/{version}",
                               "xmlns:m": f"http://xmls.skatteverket.se/se/skatteverket/ai/gemensamt/infoForBeskattning/{version}",
                               "xmlns:ku": f"http://xmls.skatteverket.se/se/skatteverket/ai/komponent/infoForBeskattning/{version}",
                               "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                               "omrade": "Kontrolluppgifter",
                               "xsi:schemaLocation": "http://xmls.skatteverket.se/se/skatteverket/ai/instans"
                                                     f"/infoForBeskattning/{version}"
                                                     "http://xmls.skatteverket.se/se/skatteverket/ai"
                                                     f"/kontrolluppgift/instans/Kontrolluppgifter_{version}.xsd"}

        Avsandare = ET.SubElement(Skatteverket, 'ku:Avsandare')
        Orgnr = f"16{company.company_registry.replace('-', '')}"
        text_map(Avsandare, {'Programnamn': 'KUfilsprogrammet',
                             'Organisationsnummer': Orgnr}
                 )

        TekniskKontaktperson = ET.SubElement(Avsandare, 'ku:TekniskKontaktperson')
        text_map(TekniskKontaktperson, {'Namn': company.partner_id.name,
                                        'Telefon': company.partner_id.phone,
                                        'Epostadress': company.partner_id.email,
                                        'Utdelningsadress1': company.partner_id.street,
                                        'Postnummer': company.partner_id.zip,
                                        'Postort': company.partner_id.city
                                        })
        text_map(Avsandare, {'Skapad': f"{datetime.now():%Y-%m-%dT%H:%M:%S}"})
        Blankettgemensamt = ET.SubElement(Skatteverket, 'ku:Blankettgemensamt')
        Uppgiftslamnare = ET.SubElement(Blankettgemensamt, 'ku:Uppgiftslamnare')

        text_map(Uppgiftslamnare, {'UppgiftslamnarePersOrgnr': Orgnr})

        Kontaktperson = ET.SubElement(Uppgiftslamnare, 'ku:Kontaktperson')
        text_map(Kontaktperson,
                 {'Namn': company.partner_id.name,
                  'Telefon': company.partner_id.phone,
                  'Epostadress': company.partner_id.email,
                  'Sakomrade': 'Skatteverket'})

        for partner_id, amount in total_amount_year.items():
            partner = self.env["res.partner"].browse(partner_id)
            is_taxable = False
            # We test if the tax identifier is valid or not
            if not partner.is_company and self._validate_partner_tax_eligibility(partner, amount):
                is_taxable = True
                identifier = partner.social_sec_nr.replace("-", "")
            # The swedish doesn't include company anymore
            # if partner.is_company and self._validate_vat_company(partner, amount):
            #     is_taxable = True
            #     identifier = partner.vat
            # If the partner is eligible we put it in the file
            # (there's no specific XML tag for company (at least on the 22.12.2022))
            if is_taxable:
                Blankett = ET.SubElement(Skatteverket, "ku:Blankett", nummer="2314")
                Arendeinformation = ET.SubElement(Blankett, "ku:Arendeinformation")
                text_map(Arendeinformation, {'Arendeagare': Orgnr,
                                             'Period': str(self.tax_year)})
                Blankettinnehall = ET.SubElement(Blankett, "ku:Blankettinnehall")
                KU65 = ET.SubElement(Blankettinnehall, "ku:KU65")

                UppgiftslamnareKU65 = ET.SubElement(KU65, 'ku:UppgiftslamnareKU65')

                text_map_faltkod(UppgiftslamnareKU65, {"UppgiftslamnarId": (Orgnr, "201"),
                                                       "NamnUppgiftslamnare": (partner.name, '202')})

                text_map_faltkod(KU65, {'Inkomstar': (str(self.tax_year), '203'),
                                        'MottagetGavobelopp': (str(int(amount)), '621'),
                                        'Specifikationsnummer': (str(partner.ref), '570')
                                        })
                InkomsttagareKU65 = ET.SubElement(KU65, 'ku:InkomsttagareKU65')
                text_map_faltkod(InkomsttagareKU65,
                                 {"Inkomsttagare": (identifier, "215"), })

        xml_str = minidom.parseString(ET.tostring(Skatteverket)).toprettyxml(indent="   ", encoding='UTF-8')

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        data = base64.b64encode(xml_str)
        attachment_id = attachment_obj.create(
            [{'name': f"Tax_{self.tax_year}_{company.name}.xml", 'datas': data}])
        # prepare download url
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        # download
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }
