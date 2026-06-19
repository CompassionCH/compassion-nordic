from odoo import models


class ResPartner(models.Model):
    _inherit = ["res.partner", "mail.thread.phone"]
    _name = "res.partner"

    def match_create_partner(self, email=None, name=None, phone=None):
        """Fetch a partner by email address or phone.
        Name is not used for matching but can be used for partner creation
        if no match is found."""
        partner = self.browse()
        if phone:
            partner = self._match_search_field("phone_mobile_search", phone)
        if not partner and email:
            partner = self._match_search_field("email", email)
        if not partner:
            sanitized_phone = self._phone_format(number=phone)
            # Fallback to given number if it cannot be sanitized and not already
            # in international E.164 format
            if sanitized_phone:
                phone = sanitized_phone
            partner = self.create(
                {
                    "name": name or email or phone,
                    "email": email,
                    "phone": phone,
                }
            )
        return partner

    def _match_search_field(self, field_name, value):
        partner = self.search(
            [(field_name, "=ilike", value)], order="customer_rank desc", limit=1
        )
        if not partner:
            partner = self.with_context(active_test=False).search(
                [(field_name, "=ilike", value)], order="customer_rank desc", limit=1
            )
            if partner:
                partner.active = True
                partner.message_post(
                    body=f"Reactivated partner based on {field_name} match"
                )
        return partner
