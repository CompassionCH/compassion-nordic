from odoo import api, models
from odoo.osv import expression

ADDRESS_FIELDS = ("street", "street2", "zip", "city", "country_id")


class ResPartner(models.Model):
    _inherit = ["res.partner", "mail.thread.phone"]
    _name = "res.partner"

    @api.model
    def match_create_partner(
        self,
        email=None,
        name=None,
        phone=None,
        firstname=None,
        lastname=None,
        address=None,
        country=None,
    ):
        """Fetch a partner by phone, then by email, or create it.

        Names are never used for matching, nor written on a partner found.
        :param address: dict of ADDRESS_FIELDS values. A partner found only
            gets it when it has no address yet, so that two addresses are
            never mixed.
        :param country: res.country used to read a national phone number
            (default: the company's country).
        """
        address = {
            key: value
            for key, value in (address or {}).items()
            if key in ADDRESS_FIELDS and value
        }
        country = country or self.env.company.country_id
        sanitized_phone = phone and self._phone_format(number=phone, country=country)
        partner = self.browse()
        if phone:
            partner = self._match_search_field(
                self._phone_match_domain(phone, sanitized_phone, country), "phone"
            )
        if not partner and email:
            partner = self._match_search_field([("email", "=ilike", email)], "email")
        if not partner:
            vals = {"email": email, "phone": sanitized_phone or phone, **address}
            if firstname or lastname:
                vals.update(firstname=firstname, lastname=lastname)
            else:
                vals["name"] = name or email or phone
            partner = self.create(vals)
        elif address and not (partner.street or partner.zip or partner.city):
            partner.write(address)
        return partner

    @api.model
    def _phone_match_domain(self, phone, sanitized_phone, country):
        """Exact match of the number, whatever the format stored on the
        partner: the international number is compared with phone_sanitized
        (one number per partner), and the international and national numbers
        with phone and mobile stripped of spaces and punctuation."""
        if not sanitized_phone:
            return [("phone_mobile_search", "=", phone)]
        domains = [
            [("phone_sanitized", "=", sanitized_phone)],
            [("phone_mobile_search", "=", sanitized_phone)],
        ]
        national_phone = self._phone_format(
            number=sanitized_phone, country=country, force_format="NATIONAL"
        )
        if national_phone:
            domains.append([("phone_mobile_search", "=", national_phone)])
        return expression.OR(domains)

    def _match_search_field(self, domain, label):
        partner = self.search(domain, order="customer_rank desc", limit=1)
        if not partner:
            partner = self.with_context(active_test=False).search(
                domain, order="customer_rank desc", limit=1
            )
            if partner:
                partner.active = True
                partner.message_post(body=f"Reactivated partner based on {label} match")
        return partner
