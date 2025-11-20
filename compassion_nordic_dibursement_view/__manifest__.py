# pylint: disable=C8101
{
    "name": "disbursement_view",
    "summary": "Create an exportable view for the excel sheet of disbursement",
    "author": "Compassion Switzerland",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-nordic",
    "category": "Uncategorized",
    "version": "18.0.1.0.0",
    "depends": ["base", "account"],
    "data": ["security/ir.model.access.csv", "views/views.xml", "security/ir.rule.xml"],
    "installable": True,
}
