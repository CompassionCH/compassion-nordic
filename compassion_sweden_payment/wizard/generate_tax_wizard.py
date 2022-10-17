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
    _inherit = "generate.tax.wizard"

    def generate_tax(self):

        company = self.env.company
        ret = self.env['account.move'].read_group([
            ('payment_state', '=', 'paid'),
            ('company_id', '=', company.id),
            ('last_payment', '>=', datetime(int(self.year), 1, 1)),
            ('last_payment', '<=', datetime(int(self.year), 12, 31)),
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
            for key, (value, falkod) in data_map.items():
                sub_with_txt(parent, f"ku:{key}", value, falkod=falkod)

        def text_map(parent, data_map: dict):
            for key, value in data_map.items():
                sub_with_txt(parent, f"ku:{key}", value)

        Skatteverket = ET.Element('Skatteverket')
        Skatteverket.attrib = {'xmlns': "http://xmls.skatteverket.se/se/skatteverket/ai/instans/infoForBeskattning/7.0",
                               'xmlns:m': "http://xmls.skatteverket.se/se/skatteverket/ai/gemensamt"
                                          "/infoForBeskattning/7.0",
                               'xmlns:ku': "http://xmls.skatteverket.se/se/skatteverket/ai/komponent"
                                           "/infoForBeskattning/7.0",
                               "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                               "omrade": "Kontrolluppgifter",
                               "xsi:schemaLocation": "http://xmls.skatteverket.se/se/skatteverket/ai/instans"
                                                     "/infoForBeskattning/7.0 "
                                                     "http://xmls.skatteverket.se/se/skatteverket/ai"
                                                     "/kontrolluppgift/instans/Kontrolluppgifter_7.0.xsd"}

        Avsandare = ET.SubElement(Skatteverket, 'ku:Avsandare')
        text_map(Avsandare, {'Programnamn': 'KUfilsprogrammet',
                             'Organisationsnummer': company.vat}
                 )

        TekniskKontaktperson = ET.SubElement(Avsandare, 'ku:TekniskKontaktperson')
        text_map(TekniskKontaktperson, {'Namn': company.partner_id.name,
                                        'Telfon': company.partner_id.phone,
                                        'Epostadress': company.partner_id.email,
                                        'Utdelningsadress1': company.partner_id.street,
                                        'Postnummer': company.partner_id.zip,
                                        'Postort': company.partner_id.city
                                        })
        text_map(Avsandare, {'Skapad': f"{datetime.now():%Y-%m-%dT%H:%M:%S}"})
        Blankettgemensamt = ET.SubElement(Skatteverket, 'ku:Blankettgemensamt')
        Uppgiftslamnare = ET.SubElement(Blankettgemensamt, 'ku:Uppgiftslamnare')

        text_map(Uppgiftslamnare, {'UppgiftslamnarePersOrgnr': company.vat})

        Kontaktperson = ET.SubElement(Uppgiftslamnare, 'ku:Kontaktperson')
        text_map(Kontaktperson,
                 {'Namn': company.partner_id.name,
                  'Telefon': company.partner_id.phone,
                  'Epostadress': company.partner_id.email,
                  'Sakomrade': 'Skatteverket'})

        for partner_id, amount in total_amount_year.items():
            partner = self.env["res.partner"].browse(partner_id)
            if partner.social_sec_nr:
                Blankett = ET.SubElement(Skatteverket, "ku:Blankett", nummer="2314")
                Arendeinformation = ET.SubElement(Blankett, "ku:Arendeinformation")
                text_map(Arendeinformation, {'Arendeagare': company.vat,
                                             'Period': str(self.year)})
                Blankettinnehall = ET.SubElement(Blankett, "ku:Blankettinnehall")
                KU65 = ET.SubElement(Blankettinnehall, "ku:KU65")

                UppgiftslamnareKU65 = ET.SubElement(KU65, 'ku:UppgiftslamnareKU65')

                text_map_faltkod(UppgiftslamnareKU65, {"UppgiftslamnarId": (company.vat, "201"),
                                                       "NamnUppgiftslamnare": (partner.name, '202')})

                text_map_faltkod(KU65, {'Inkomstar': (str(self.year), '203'),
                                        'MottagetGavobelopp': (str(int(amount)), '621'),
                                        'Specifikationsnummer': (str(partner.ref), '570')
                                        })
                InkomsttagareKU65 = ET.SubElement(KU65, 'ku:InkomsttagareKU65')
                text_map_faltkod(InkomsttagareKU65, {"Inkomsttagare": (partner.social_sec_nr, "215"), })

        xmlstr = minidom.parseString(ET.tostring(Skatteverket)).toprettyxml(indent="   ")

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        data = base64.b64encode(str.encode(xmlstr, 'utf-8'))
        attachment_id = attachment_obj.create(
            [{'name': f"Tax_{self.year}_{company.name}.xml", 'datas': data}])
        # prepare download url
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        # download
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }
