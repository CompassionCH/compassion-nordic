# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Compassion Norden base config",
    "version": "14.0.0.0.0",
    "license": "AGPL-3",
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "category": "Localization",
    "depends": [
        "product",
        "compassion_nordic_accounting",
        "compassion_denmark_payment",
        "compassion_norway_payment",
        "compassion_sweden_payment",
    ],
    "data": [
        "data/norden_product.xml",
        "data/res.users.csv",
    ],
}
