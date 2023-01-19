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


class GenerateTaxWizard(models.TransientModel):
    _inherit = "generate.tax.wizard"

    def generate_tax(self):
        self._del_old_entry()
        company = self.env.company
        if company.country_id.name != "Norway":
            return super().generate_tax()
        ret = self.env['account.move'].read_group([
            ('payment_state', '=', 'paid'),
            ('company_id', '=', company.id),
            ('last_payment', '>=', datetime(int(self.tax_year), 1, 1)),
            ('last_payment', '<=', datetime(int(self.tax_year), 12, 31)),
            ('invoice_category', 'in', ['fund', 'sponsorship']),
        ], ['amount_total', 'last_payment'],
            groupby=['partner_id'], lazy=False)
        total_amount_year = {}
        for a in ret:
            if a['partner_id'][0] not in total_amount_year:
                total_amount_year[a['partner_id'][0]] = 0
            total_amount_year[a['partner_id'][0]] += a['amount_total']
        grouped_amounts = {a['partner_id'][0]: a['amount_total'] for a in ret if a['amount_total'] >= 500}

        def sub_with_txt(parent, tag, text, **extra):
            elem = ET.SubElement(parent, tag, extra)
            elem.text = text
            return elem

        def text_map(parent, data_map: dict):
            for key, value in data_map.items():
                sub_with_txt(parent, key, value)

        melding = ET.Element('melding')
        melding.attrib = {'xmlns': "urn:ske:fastsetting:innsamling:gavefrivilligorganisasjon:v2",
                          'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
                          ' xsi:schemaLocation': "urn:ske:fastsetting:innsamling:gavefrivilligorganisasjon:v2 "
                                                 "gavefrivilligorganisasjon_v2_0.xsd "

                          }

        leveranse = ET.SubElement(melding, 'leveranse')
        kildesystem = ET.SubElement(leveranse, 'kildesystem')
        kildesystem.text = "Kildesystemet v2.0.5"
        oppgavegiver = ET.SubElement(leveranse, 'oppgavegiver')
        text_map(oppgavegiver, {'organisasjonsnummer': company.company_registry.replace(' ', ''), 'organisasjonsnavn': company.name})
        kontaktinformasjon = ET.SubElement(oppgavegiver, 'kontaktinformasjon')
        text_map(kontaktinformasjon,
                 {'navn': company.partner_id.name, 'telefonnummer': company.partner_id.phone,
                  'varselEpostadresse': company.partner_id.email,
                  })
        text_map(leveranse, {'inntektsaar': str(self.tax_year),
                             'oppgavegiversLeveranseReferanse': f'REF{self.tax_year}{datetime.now():%d%m%Y}',
                             'leveransetype': 'ordinaer'})
        total_amount = 0
        total_partner = 0
        for partner_id, amount in grouped_amounts.items():
            partner = self.env['res.partner'].browse(partner_id)
            is_taxable = False
            # We test the tax identifier to make sure it is valid
            if (not partner.is_company) and self._validate_partner_tax_eligibility(partner, amount):
                is_taxable = True
                identifier = partner.social_sec_nr
            elif partner.is_company and self._validate_vat_company(partner, amount):
                is_taxable = True
                identifier = partner.vat
            # If the partner is eligible we put it in the file
            # (there's no specific XML tag for company (at least on the 22.12.2022))
            if is_taxable:
                oppgave = ET.SubElement(leveranse, 'oppgave')
                oppgaveeier = ET.SubElement(oppgave, 'oppgaveeier')
                text_map(oppgaveeier, {"foedselsnummer": str(identifier), 'navn': partner.name})
                text_map(oppgave, {'beloep': str(int(amount))})
                total_amount += amount
                total_partner += 1
        oppgaveoppsummering = ET.SubElement(leveranse, 'oppgaveoppsummering')
        text_map(oppgaveoppsummering, {'antallOppgaver': str(total_partner),
                                       'sumBeloep': str(int(total_amount))})
        xmlstr = minidom.parseString(ET.tostring(melding)).toprettyxml(indent="   ", encoding='UTF-8')

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        data = base64.b64encode(xmlstr)
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

