from ftplib import print_line

from phonenumbers.phonenumberutil import NumberParseException

from odoo import models
from odoo.addons.phone_validation.tools import phone_validation
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
            partner = self.create(
                {
                    "name": name or email or phone,
                    "email": email,
                    "phone": sanitized_phone,
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


def fix_phone():
    non_fixable = 0
    fixable = 0
    partners = env['res.partner'].search([])
    print(f"looking at {len(partners)} partners\n")
    for partner in partners:
        #print(f' ----------------------- {partner.phone} -----------------------')
        country = partner._phone_get_country().get(partner.id)
        if not country:
            non_fixable += 1
            continue
        try:
            phone_validation.phone_parse(partner.phone, country.code)
        except:
            if partner.phone:
                print(f" ---> PHONE {partner.phone} IS NO BUENO ({partner.phone_sanitized})\n")
            try:
                validated_phone = partner._phone_format(partner.phone, country)
                print(f" ---> VALIDATED PHONE IS  {validated_phone}\n")
            except:
                non_fixable += 1
                continue
            if not validated_phone:
                non_fixable += 1
            else:
                print(f"PHONE {partner.phone} CAN BE FIXED AS {validated_phone}\n")
                fixable += 1
    print(f"Out of  {len(partners)}, {fixable} phones cas be fixed, {non_fixable} phones cannot.\n")

def fixit():
    non_fixable = 0
    stand_fixable = 0
    stand = 0
    fixable = 0
    partners = env['res.partner'].search([])
    print(f"looking at {len(partners)} partners\n")
    for partner in partners:
        try:
            parsed_number = phonenumbers.parse(partner.phone, None)
            if phonenumbers.is_valid_number(parsed_number):
                sanitized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                if sanitized != partner.phone:
                    stand_fixable += 1
                else:
                    stand += 1
                continue
        except NumberParseException as numEx:
            try:
                if numEx.error_type == NumberParseException.INVALID_COUNTRY_CODE and partner.country_id:
                    parsed_number = phonenumbers.parse(partner.phone, partner.country_id.code)
                    if phonenumbers.is_valid_number(parsed_number):
                        sanitized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        if sanitized != partner.phone:
                            print(f"BEFORE WAS {partner.phone} FOR COUNTRY {partner.country_id.code}, NOW IS {sanitized}")
                            fixable += 1
            except Exception as ex:
                print(ex)
        except Exception as ex:
            print(ex)
        non_fixable += 1
    print(f"{stand} dont need to be fixed | {stand_fixable} stand can be fixed | {fixable} non stand phones can be fixed | {non_fixable} phones cannot.\n")
    print(f"So out of {len(partners)} a total of {stand_fixable + fixable} will be updated.\n")


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
            except Exception as ex:
                pass
        except Exception as ex:
            pass
    partners_to_update = partners_to_update[:10]
    for partner, standardized_phone in partners_to_update:
        print(f"WILL FIX PARTNER {partner.id} WITH PHONE {partner.phone} TO HAVE STANDARDISED PHONE {standardized_phone}")
        partner.with_context(tracking_disable=True).write({'phone': standardized_phone})
    print(f"Out of  {len(partners)} | {len(partners_to_update)} will be updated\n")