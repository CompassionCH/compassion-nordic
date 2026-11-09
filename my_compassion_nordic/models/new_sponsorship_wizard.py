from odoo import fields, models
from odoo.exceptions import ValidationError

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    _product_display_price,
)

# What the plan radios of the checkout post as "sponsorship_plus": "0" is the
# sponsorship alone, "1" the sponsorship with the Plus contribution.
PLAN_VALUES = {"0": "standard", "1": "plus"}

# Currencies whose amount the copy writes out in words: the Swedish krona and
# the Norwegian and Danish krone. Any other currency is written with its
# symbol.
KRONA_CURRENCIES = ("SEK",)
KRONE_CURRENCIES = ("NOK", "DKK")


class NewSponsorshipWizard(models.TransientModel):
    """The Nordic checkout asks the sponsor to choose between the sponsorship
    and the sponsorship with the Plus contribution (product fund_gen). Both
    are offered as radio buttons, neither picked in advance, and a standard
    sponsorship cannot be finished until one is.
    """

    _inherit = "new.sponsorship.wizard"

    # The plan the sponsor picked, empty until they pick one: the False of
    # sponsorship_plus also means the sponsorship alone, so it cannot tell
    # "not chosen yet" apart. A re-render of the step checks the radio picked.
    sponsorship_plan = fields.Selection(
        [("standard", "Sponsorship"), ("plus", "Sponsorship Plus")]
    )

    def update(self, post):
        """Read the plan radios.

        The radio value is parsed here and removed from what the base method
        reads: it converts sponsorship_plus with bool(), which takes the "0"
        of the standard plan for the Plus. Any value other than "0" or "1"
        leaves the choice as it was.
        """
        post = dict(post)
        value = post.pop("sponsorship_plus", None)
        plan = PLAN_VALUES.get(value) if isinstance(value, str) else None
        if plan:
            self.write({"sponsorship_plan": plan, "sponsorship_plus": plan == "plus"})
        return super().update(post)

    def finish_sponsorship(self):
        """Refuse a standard sponsorship whose plan was not chosen.

        Checked before anything is created, like the base checks of the
        consent and the payment mode. The radios are required in the page,
        but a posted form can omit them. Write&Pray offers no plan.
        """
        self.ensure_one()
        if self.sponsorship_type != "write_and_pray":
            if not self.sponsorship_plan:
                raise ValidationError(
                    self.env._(
                        "Please choose one of the two sponsorship options"
                        " before continuing."
                    )
                )
            # sponsorship_plus is what the base method reads to keep or drop
            # the fund_gen line of the contract.
            self.sponsorship_plus = self.sponsorship_plan == "plus"
        return super().finish_sponsorship()

    # === Copy of the plan choice ===

    def _my2_plan_product(self, default_code, website):
        """The product a plan is named after, by the same lookup as the
        amounts (my_compassion's _product_display_price): the website
        company's own product, else a shared one."""
        company = website.company_id
        products = (
            self.env["product.template"]
            .sudo()
            .with_company(company)
            .search(
                [
                    ("default_code", "=", default_code),
                    ("company_id", "in", [company.id, False]),
                ]
            )
        )
        return products.filtered(lambda p: p.company_id == company)[:1] or products[:1]

    def _my2_plan_name(self, default_code, website, fallback):
        """The product's name in the visitor's language.

        The English name of these products is the back office's (e.g. "CDSP -
        contract only"). A language without a name of its own shows that
        one, so the visitor then gets the fallback label instead, which is
        translated like the rest of the page.
        """
        product = self._my2_plan_product(default_code, website)
        name = product.name
        if not product or name == product.with_context(lang="en_US").name:
            return fallback
        return name

    def _my2_amount_words(self, amount, currency):
        """An amount with its currency as a sentence writes it ("60 kronor")."""
        if currency.name in KRONA_CURRENCIES:
            return self.env._("%(amount)s kronor", amount=amount)
        if currency.name in KRONE_CURRENCIES:
            return self.env._("%(amount)s kroner", amount=amount)
        return f"{amount} {currency.symbol}"

    def _my2_plan_choice(self, website):
        """Everything the plan radios and their explanation show.

        Names come from the products, amounts from the website's pricelist,
        so each country's own products and prices show without anything
        written per country. The Plus option shows the total: the
        sponsorship and the fund_gen contribution together.

        Returns a dict:
        - options: one dict per radio, with its posted value, input id,
          name, price (e.g. "360 kr/month") and whether it is checked.
        - question: the text of the link that opens the explanation.
        - contribution: the explanation's sentence naming the extra amount.
        """
        self.ensure_one()
        currency = website.currency_id
        base_amount = float(_product_display_price("sponsorship", website) or 0)
        extra_amount = float(_product_display_price("fund_gen", website) or 0)
        standard_name = self._my2_plan_name(
            "sponsorship", website, self.env._("Sponsorship")
        )
        plus_name = self._my2_plan_name(
            "fund_gen", website, self.env._("Sponsorship Plus")
        )

        def price(amount):
            return self.env._(
                "%(amount)s %(currency)s/month",
                amount=f"{amount:g}",
                currency=currency.symbol,
            )

        return {
            "options": [
                {
                    "value": "0",
                    "input_id": "sponsorship_plan_standard",
                    "name": standard_name,
                    "price": price(base_amount),
                    "checked": self.sponsorship_plan == "standard",
                },
                {
                    "value": "1",
                    "input_id": "sponsorship_plan_plus",
                    "name": plus_name,
                    "price": price(base_amount + extra_amount),
                    "checked": self.sponsorship_plan == "plus",
                },
            ],
            "question": self.env._("What does %(plan)s mean?", plan=plus_name),
            "contribution": self.env._(
                "Besides helping your sponsored child to develop physically,"
                " economically, socially and spiritually, you give %(extra)s"
                " extra for needs the sponsorship does not cover.",
                extra=self._my2_amount_words(f"{extra_amount:g}", currency),
            ),
        }
