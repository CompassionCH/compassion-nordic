from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return
    xml_ids = [
        "paperformat_childpack", "paperformat_a4_childpack"
    ]
    openupgrade.rename_xmlids(cr, [
        (f"child_nordic.{xmlid}", f"child_compassion.{xmlid}") for xmlid in xml_ids
    ], allow_merge=True)
