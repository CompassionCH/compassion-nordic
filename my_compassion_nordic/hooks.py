PROVIDER_CODE = "adyen"
DIGITAL_MODE_NAME = "Card (Adyen)"


def _ensure_digital_modes(env):
    """Create the per-company digital payment mode where missing.

    Companies and payment providers carry no xmlids on the Nordic DB (created
    via UI/prod), so resolution is by provider code, not data refs. One mode
    per company that owns a PROVIDER_CODE provider; created UNPUBLISHED -
    publishing a mode is each country's explicit opt-in.
    """
    method = env.ref("my_compassion.payment_method_psp_token")
    providers = (
        env["payment.provider"]
        .with_context(active_test=False)
        .search([("code", "=", PROVIDER_CODE)])
    )
    modes = env["account.payment.mode"]
    for provider in providers:
        # active_test=False: an ops-archived mode must not be re-created
        mode = env["account.payment.mode"].with_context(active_test=False).search(
            [
                ("company_id", "=", provider.company_id.id),
                ("payment_provider_id", "=", provider.id),
            ],
            limit=1,
        )
        if not mode:
            mode = env["account.payment.mode"].create(
                {
                    "name": DIGITAL_MODE_NAME,
                    "company_id": provider.company_id.id,
                    "payment_method_id": method.id,
                    "bank_account_link": "variable",
                    "payment_order_ok": False,
                    "payment_provider_id": provider.id,
                }
            )
        modes |= mode
    return modes


def post_init_hook(env):
    _ensure_digital_modes(env)
