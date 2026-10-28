from odoo import models


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

    # === National identity number on the post-payment details form ===

    def _my2_collects_ssn(self):
        """Whether this signup's company asks its sponsors for their SSN."""
        self.ensure_one()
        return bool(self.company_id.sudo().my2_collect_ssn)

    def _my2_ssn_country_code(self):
        """The country whose report this signup's gift would go into."""
        self.ensure_one()
        return self.company_id.sudo().country_id.code or ""

    def _my2_details_extra_partner_vals(self, values):
        """Save the sponsor's national identity number.

        Only what the company actually collects, and only a number that
        classified as storable - the controller has already rejected a typo,
        so anything arriving here is valid for some Nordic country. An empty
        value is left out rather than written: the field is optional, and
        blanking a number already on file would lose it.
        """
        vals = super()._my2_details_extra_partner_vals(values)
        ssn = (values.get("social_sec_nr") or "").strip()
        if ssn and self._my2_collects_ssn():
            vals["social_sec_nr"] = ssn
        return vals

    def _my2_details_extra_prefill(self):
        vals = super()._my2_details_extra_prefill()
        if self._my2_collects_ssn():
            vals["social_sec_nr"] = self.partner_id.sudo().social_sec_nr or ""
        return vals
