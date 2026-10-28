from odoo import models

from .res_partner import SSN_FORMATS


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    def _my2_fixit_configs(self):
        """Supply the Nordic charge-failure emails to the generic engine."""
        first = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_first",
            raise_if_not_found=False,
        )
        final = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_final",
            raise_if_not_found=False,
        )
        if not first or not final:
            return super()._my2_fixit_configs()
        return {"first": first, "final": final}

    def _my2_portal_invitation_config(self):
        config = self.env.ref(
            "my_compassion_nordic.config_portal_invitation",
            raise_if_not_found=False,
        )
        return config or super()._my2_portal_invitation_config()

    # === Post-payment details form ===

    def _my2_details_mandatory(self):
        """The details form is a required step on the Nordic sites: it stays
        due after Stripe supplied the payer's name, so the sponsor still
        confirms who writes to the child and gives their national identity
        number, and it has no "do this later"."""
        self.ensure_one()
        return True

    def _my2_collects_ssn(self):
        """Whether this signup's company asks its sponsors for their SSN.

        Its flag, and a country whose number the form knows how to check
        (SSN_FORMATS), so the flag switched on for any other country cannot
        make the field refuse every value.
        """
        self.ensure_one()
        company = self.company_id.sudo()
        return bool(company.my2_collect_ssn and company.country_id.code in SSN_FORMATS)

    def _my2_ssn_country_code(self):
        """The country whose tax report this signup's gift goes into."""
        self.ensure_one()
        return self.company_id.sudo().country_id.code or ""

    def _my2_details_extra_partner_vals(self, values):
        """Save the payer's national identity number.

        Only what the company actually collects, in the form its tax report
        uses. The controller has already refused a number that is not valid
        for the company's country, so anything arriving here normalises. An
        empty value is left out rather than written: the field is optional,
        and blanking a number already on file would lose it.
        """
        vals = super()._my2_details_extra_partner_vals(values)
        ssn = values.get("social_sec_nr")
        if ssn and self._my2_collects_ssn():
            normalized = self.env["res.partner"]._my2_normalize_ssn(
                ssn, self._my2_ssn_country_code()
            )
            if normalized:
                vals["social_sec_nr"] = normalized
        return vals

    def _my2_apply_details(self, values):
        """Save the details form, keeping the payer and the letter writer apart.

        The payer (partner_id) is who Stripe charged. Their name, once Stripe
        supplied it, is the one the tax report and the gift receipts carry,
        together with the national identity number. The form's name is who
        writes to the child, and the form says to enter someone else's name
        when they do.

        - The payer still carries the placeholder (Stripe sent no name): the
          form's name is the payer's, as on every other site.
        - The form keeps the payer's full name, maybe split differently: the
          same person, so the corrected split is written on the payer.
        - Another name: that person becomes the contract's correspondent,
          with the phone number. The payer keeps their name and gets only
          the identity number. The correspondent change syncs with GMC, so
          it runs as a queue job (_my2_assign_letter_writer): a GMC failure
          must never turn the sponsor's submission into an error page.
        """
        self.ensure_one()
        payer = self.partner_id.sudo()
        firstname = values.get("firstname") or ""
        lastname = values.get("lastname") or ""
        if payer.my2_name_placeholder:
            return super()._my2_apply_details(values)
        if _full_name(firstname, lastname) == _full_name(
            payer.firstname, payer.lastname
        ):
            if (payer.firstname or "", payer.lastname or "") != (firstname, lastname):
                payer.write(
                    {"firstname": firstname or False, "lastname": lastname or False}
                )
            return super()._my2_apply_details(values)
        letter_writer = self._my2_create_letter_writer(values)
        self.sudo().with_delay_sh(
            "_my2_assign_letter_writer",
            letter_writer.id,
            description="Assign the letter writer of a MyCompassion signup",
            identity_key=f"{self._name}._my2_assign_letter_writer.{self.id}",
        )
        return super()._my2_apply_details(
            {**values, "firstname": "", "lastname": "", "phone": ""}
        )

    def _my2_assign_letter_writer(self, letter_writer_id):
        """Make the letter writer the correspondent of this sponsorship.

        Through the ordinary write, which updates the commitment at GMC once
        the sponsorship has one. Before that, GMC still has to know the
        letter writer when the pending sponsorship upsert names them, hence
        the constituent upsert first.

        Elevated: queued from the public details form, so the job runs as
        the public user.
        """
        self.ensure_one()
        sponsorship = self.sudo()
        letter_writer = self.env["res.partner"].sudo().browse(letter_writer_id)
        if not sponsorship.gmc_commitment_id and not letter_writer.global_id:
            letter_writer.upsert_constituent().process_messages()
        sponsorship.correspondent_id = letter_writer

    def _my2_create_letter_writer(self, values):
        """The correspondent the details form names, as a new contact.

        Never matched against existing partners: the form is public, and
        matching would let whoever holds the token make someone else's
        record the correspondent of this sponsorship. Staff merge real
        duplicates. The letter writer speaks the payer's languages and lives
        in the payer's country until told otherwise.
        """
        self.ensure_one()
        payer = self.partner_id.sudo()
        return (
            self.env["res.partner"]
            .sudo()
            .create(
                {
                    "firstname": values.get("firstname") or False,
                    "lastname": values.get("lastname") or False,
                    "phone": values.get("phone") or False,
                    "lang": payer.lang,
                    "country_id": payer.country_id.id,
                    "spoken_lang_ids": [(6, 0, payer.spoken_lang_ids.ids)],
                }
            )
        )


def _full_name(firstname, lastname):
    """A name as one comparable string: case and spacing do not matter."""
    return " ".join(f"{firstname or ''} {lastname or ''}".split()).casefold()
