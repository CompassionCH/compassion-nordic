from odoo import models

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
