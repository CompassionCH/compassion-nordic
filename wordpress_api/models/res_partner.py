from phonenumbers.phonenumberutil import NumberParseException

from odoo import models
import phonenumbers


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
            # Fallback to given number if it cannot be sanitized
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

def standardise_partner_phones():
    partners_to_update = []
    partners = env['res.partner'].search([])
    for partner in partners:
        try:
            parsed_number = phonenumbers.parse(partner.phone, None)
            if phonenumbers.is_valid_number(parsed_number):
                sanitized_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                if sanitized_phone != partner.phone:
                    partners_to_update.append((partner, sanitized_phone))
                continue
        except NumberParseException as numEx:
            try:
                if numEx.error_type == NumberParseException.INVALID_COUNTRY_CODE and partner.country_id:
                    parsed_number = phonenumbers.parse(partner.phone, partner.country_id.code)
                    if phonenumbers.is_valid_number(parsed_number):
                        sanitized_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if sanitized_phone != partner.phone:
                            partners_to_update.append((partner, sanitized_phone))
            except:
                pass
        except:
            pass
    partners_to_update = partners_to_update[:10]
    for partner, standardized_phone in partners_to_update:
        print(f"WILL FIX PARTNER {partner.id} WITH PHONE {partner.phone} TO HAVE STANDARDISED PHONE {standardized_phone}")
        partner.with_context(tracking_disable=True).write({'phone': standardized_phone})
    print(f"Out of  {len(partners)} | {len(partners_to_update)} will be updated\n")