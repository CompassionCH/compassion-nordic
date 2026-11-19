# Compassion Nordic · Odoo 18

These addons provide Nordic sponsorship, accounting and sponsor portal features. Only
the Nordic deployment has them. It runs Odoo Enterprise. Denmark, Norway and Sweden each
have a payment addon. The portal also ships Finnish translations.

## Dependencies and translations

Declare the addons you use in the manifest's `depends`. Odoo refuses a dependency cycle
between addons: check the whole chain before adding a dependency on another repository's
addon. Addons here can depend on `compassion-modules`, `compassion-accounting` and
`compassion-website`. Shared addons never depend on addons here. Put country-specific
payment changes in the relevant country addon. Swedish SEPA file adjustments belong in
`account_payment_order_sepa_se`. As an existing exception, the regional
`compassion_nordic_accounting` depends on the Swedish Enterprise export
`l10n_se_sie4_export`.

If the module has catalogs, update its existing locales. For its first catalogs,
identify installing countries from country-addon dependencies or deployment
configuration. Ask the maintainer if coverage is unclear. Use `sv_SE` for Sweden,
`nb_NO` for Norway, `da_DK` for Denmark and `fi_FI` for Finland. A Denmark-only addon
needs only `da_DK` for its first catalog.

## Where to find the rules

When a task changes code here, open the shared rule subjects it needs. If the toolkit
plugins are available, use their skills `code-rules:rules` and `odoo-rules:rules`;
otherwise fetch the published rules into a temporary folder:
`(d="$(mktemp -d)" && git clone -q --depth 1 --branch main https://github.com/CompassionCH/compassion-agent-toolkit.git "$d" && echo "$d")`.
There, each index is `plugins/<plugin>/skills/rules/SKILL.md`. If the sandbox blocks the
network, ask the user to run the command, or read the indexes online:
[code-rules](https://github.com/CompassionCH/compassion-agent-toolkit/blob/main/plugins/code-rules/skills/rules/SKILL.md)
[odoo-rules](https://github.com/CompassionCH/compassion-agent-toolkit/blob/main/plugins/odoo-rules/skills/rules/SKILL.md)

## Before opening a PR

The pre-commit workflow does not run on PRs to `18.0` yet. Before opening a PR, run
`pre-commit run --from-ref origin/18.0 --to-ref HEAD` to check the files your branch
changed. Use `pre-commit install` to enable the hooks on commit. Run the affected Odoo
tests separately.

Then run the rules review in `review.md`, linked from the code-rules index. Use the
`code-rules:rules-reviewer` subagent when the plugin is available; otherwise give a
fresh read-only session the published reviewer prompt,
`plugins/code-rules/agents/rules-reviewer.md` in that folder
([online](https://github.com/CompassionCH/compassion-agent-toolkit/blob/main/plugins/code-rules/agents/rules-reviewer.md)).
Only if neither is possible, say in the PR description that no rules review ran. Record
findings, coverage gaps and their disposition there.
