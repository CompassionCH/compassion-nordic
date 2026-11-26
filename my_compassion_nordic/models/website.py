from odoo import api, models

# The page of each country's public website where a visitor starts a
# sponsorship, keyed on the country code of the website's company. A country
# without an entry keeps the sponsor inside MyCompassion.
SPONSOR_CHILD_URLS = {
    "SE": "https://www.compassion.se/bli-fadder-genom-compassion/",
    "NO": "https://www.compassion.no/bli-compassion-fadder/",
    "DK": "https://www.compassiondk.dk/bliv-compassion-fadder/",
}


class Website(models.Model):
    _inherit = "website"

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        for website, vals in zip(websites, vals_list, strict=True):
            if website.is_my_compassion:
                website._my2_seed_nordic_settings(vals)
        return websites

    def write(self, vals):
        """A website that becomes a MyCompassion website gets the Nordic
        settings once, on that change: a website already flagged keeps
        whatever staff set since."""
        becoming = self.browse()
        if vals.get("is_my_compassion"):
            becoming = self.filtered(lambda website: not website.is_my_compassion)
        res = super().write(vals)
        becoming._my2_seed_nordic_settings(vals)
        return res

    def _my2_seed_nordic_settings(self, vals=None):
        """Set the Nordic MyCompassion settings: the "sponsor a child" links
        lead to the country's public website, where that setting is still
        empty, and the list of children waiting for a sponsor mixes the
        countries. A value given in vals, the values the website is being
        created or flagged with, is kept."""
        vals = vals or {}
        self._my2_seed_sponsor_child_url()
        if "my2_child_list_order" not in vals:
            self.sudo().my2_child_list_order = "mix_countries"

    def _my2_seed_sponsor_child_url(self):
        """Fill sponsor_child_url from the country of each website's company.

        Only an empty value is filled: a URL staff set in the settings always
        stays. The country is read in Python because res.company.country_id
        is a non-stored compute that cannot be searched. Returns the websites
        that were filled.
        """
        filled = self.browse()
        for website in self.sudo():
            url = SPONSOR_CHILD_URLS.get(website.company_id.country_id.code)
            if url and not website.sponsor_child_url:
                website.sponsor_child_url = url
                filled |= website
        return filled
