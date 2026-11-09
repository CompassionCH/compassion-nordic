from odoo.tests import TransactionCase, tagged
from odoo.tests.common import HttpCase, new_test_user

from ..hooks import _seed_website_settings
from ..models.website import SPONSOR_CHILD_URLS

SPONSOR_URL = "https://sponsor.example.org/start/"
LIST_HREF = 'href="/my2/sponsorships"'


@tagged("post_install", "-at_install")
class TestSponsorChildLinks(HttpCase):
    """The links that start a new sponsorship lead to the website's
    sponsor_child_url, or to MyCompassion's list of children when it is
    empty."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The test client talks to 127.0.0.1: the MyCompassion website gets
        # that domain, like the sponsors' requests in production.
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.write({"domain": cls.base_url(), "sponsor_child_url": False})
        cls.login = "my2-sponsor-child-link"
        new_test_user(cls.env, login=cls.login, groups="base.group_portal")

    def _page(self, route):
        self.authenticate(self.login, self.login)
        page = self.url_open(route)
        self.assertEqual(page.status_code, 200)
        return page.text

    def assertLinksFollowSetting(self, route):
        """The page renders its link to the list with the setting empty, and
        the very same links lead to the setting's URL once it is set."""
        page = self._page(route)
        to_list = page.count(LIST_HREF)
        self.assertGreaterEqual(to_list, 1)
        self.assertNotIn(SPONSOR_URL, page)

        self.website.sponsor_child_url = SPONSOR_URL
        page = self._page(route)
        to_setting = page.count(f'href="{SPONSOR_URL}"')
        self.assertGreaterEqual(to_setting, 1)
        self.assertEqual(page.count(LIST_HREF), to_list - to_setting)

    def test_new_sponsorship_button_of_children_page(self):
        self.assertLinksFollowSetting("/my2/children")

    def test_become_a_sponsor_tile_of_dashboard(self):
        self.assertLinksFollowSetting("/my2/dashboard")


@tagged("post_install", "-at_install")
class TestSponsorChildUrlSeed(TransactionCase):
    """The URL is filled from the country of the website's company, only
    where it is empty. Every MyCompassion website mixes the countries of its
    list of children."""

    def _website(self, country_code, url=False):
        country = self.env["res.country"].search([("code", "=", country_code)])
        company = self.env["res.company"].create(
            {"name": f"Seed Test {country_code}", "country_id": country.id}
        )
        return self.env["website"].create(
            {
                "name": f"Seed Test {country_code}",
                "company_id": company.id,
                "sponsor_child_url": url,
            }
        )

    def test_empty_url_is_filled_by_country(self):
        websites = {code: self._website(code) for code in ("SE", "NO", "DK")}
        filled = (
            self.env["website"].union(*websites.values())._my2_seed_sponsor_child_url()
        )
        self.assertEqual(len(filled), 3)
        for code, website in websites.items():
            self.assertEqual(website.sponsor_child_url, SPONSOR_CHILD_URLS[code])

    def test_other_country_stays_empty(self):
        website = self._website("FI")
        self.assertFalse(website._my2_seed_sponsor_child_url())
        self.assertFalse(website.sponsor_child_url)

    def test_url_set_by_staff_is_kept(self):
        website = self._website("SE", url=SPONSOR_URL)
        self.assertFalse(website._my2_seed_sponsor_child_url())
        self.assertEqual(website.sponsor_child_url, SPONSOR_URL)

    def test_hook_leaves_other_websites_alone(self):
        website = self._website("SE")
        self.assertFalse(website.is_my_compassion)
        _seed_website_settings(self.env)
        self.assertFalse(website.sponsor_child_url)
        self.assertEqual(website.my2_child_list_order, "waiting")

    def test_hook_mixes_countries_on_my_compassion_websites(self):
        websites = self._website("SE") | self._website("FI")
        websites.write({"is_my_compassion": True})
        self.assertEqual(set(websites.mapped("my2_child_list_order")), {"waiting"})
        _seed_website_settings(self.env)
        self.assertEqual(
            set(websites.mapped("my2_child_list_order")), {"mix_countries"}
        )
