ADYEN_CODE = "adyen"

# Provider codes able to hold the sponsor card of the digital charge engine.
# The mode name carries the provider brand so ops can tell modes apart.
DIGITAL_MODE_NAMES = {
    "adyen": "Card (Adyen)",
    "stripe": "Card (Stripe)",
}


def _ensure_digital_modes(env, providers=None):
    """Create the per-company digital payment mode where missing.

    Companies and payment providers carry no xmlids on the Nordic DB (created
    via UI/prod), so resolution is by provider code, not data refs. One mode
    per provider whose code supports the digital charge engine. Modes are
    created UNPUBLISHED. Publishing a mode is each country's explicit opt-in.
    Pass providers to limit the pass to those records, the default scans the
    whole database.
    """
    method = env.ref("my_compassion.payment_method_psp_token")
    if providers is None:
        providers = (
            env["payment.provider"]
            .with_context(active_test=False)
            .search([("code", "in", list(DIGITAL_MODE_NAMES))])
        )
    modes = env["account.payment.mode"]
    for provider in providers:
        # active_test=False: an ops-archived mode must not be re-created
        mode = (
            env["account.payment.mode"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_id", "=", provider.company_id.id),
                    ("payment_provider_id", "=", provider.id),
                ],
                limit=1,
            )
        )
        if not mode:
            mode = env["account.payment.mode"].create(
                {
                    "name": DIGITAL_MODE_NAMES[provider.code],
                    "company_id": provider.company_id.id,
                    "payment_method_id": method.id,
                    "bank_account_link": "variable",
                    "payment_order_ok": False,
                    "payment_provider_id": provider.id,
                }
            )
        modes |= mode
    return modes


def _seed_sponsor_child_urls(env):
    """Point each MyCompassion website's "sponsor a child" links at its
    country's public website, where its setting is still empty."""
    websites = env["website"].search([("is_my_compassion", "=", True)])
    return websites._my2_seed_sponsor_child_url()


def post_init_hook(env):
    _ensure_digital_modes(env)
    env["res.company"]._my2_seed_collect_ssn()
    _seed_sponsor_child_urls(env)
