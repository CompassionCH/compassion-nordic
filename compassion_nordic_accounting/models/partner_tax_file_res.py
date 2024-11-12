from odoo import api, models, fields


class PartnerTaxFileRes(models.Model):
    _name = "res.partner.tax.file.result"
    _description = "Partner that has been exported or not for a taxation file are stored in this model"

    tax_company_id = fields.Many2one("res.company", "Company tax")
    tax_year = fields.Char("Taxation year")
    # We store the field to be able to group by it
    partner_country = fields.Char("Partner country", related="partner_id.country_id.code", store=True)
    partner_id = fields.Many2one("res.partner", "Partner")
    partner_ssn = fields.Char("Social Security Number", related="partner_id.social_sec_nr")
    partner_vat = fields.Char("VAT number", related="partner_id.vat")
    partner_email = fields.Char("Partner email", related="partner_id.email")
    partner_phone = fields.Char("Partner phone", related="partner_id.phone")
    yearly_amount = fields.Monetary(
        string="Yearly amount",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one('res.currency', related="tax_company_id.currency_id")
    state = fields.Selection([("valid", "Valid"),
                              ("empty_vat", "Company VAT is empty"),
                              ("invalid_vat", "Company VAT is not correct"),
                              ("under_18", "Partner SSN is not 18 years old"),
                              ("invalid_ssn", "SSN format is not correct"),
                              ("empty_ssn", "SSN field is empty")],
                             )
