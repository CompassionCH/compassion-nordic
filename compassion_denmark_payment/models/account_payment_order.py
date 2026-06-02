##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models

from . import beservice


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def format_transmission_number(self):
        return "{}1".format(self.create_date.strftime("%d%m%y"))

    def generate_payment_file(self):
        self.ensure_one()
        if self.payment_method_id.code != "denmark_direct_debit":
            return super().generate_payment_file()

        data_delivery = beservice.DataDeliveryCollection(
            data_supplier_number=self.payment_mode_id.initiating_party_scheme,
            subsystem="BS1",
            delivery_type=beservice.DeliveryType.COLLECTION_DATA,
            delivery_identification=1,
        )

        data_delivery.add_section(
            data_supplier_id=self.payment_mode_id.initiating_party_identifier,
            pbs_number=self.payment_mode_id.initiating_party_issuer,
            debtor_group_number=1,
        )

        # Here I probably need to create a single data_delivery.sections[0].add_payment instead of one in every loop
        # so that I can merge the different products under a single bill
        # Just have to check if it doesn't break other behavior, also could be good to know why this behavior changed

        grouped_payments = {}

        for pymt_trx in self.payment_ids:
            group_key = pymt_trx.payment_line_ids[0].move_line_id.move_id.line_ids.mapped("contract_id").group_id
            if group_key not in grouped_payments:
                grouped_payments[group_key] = []
            grouped_payments[group_key].append(pymt_trx)

        for contract_group in grouped_payments:
            text_lines = []
            for pymt_trx in grouped_payments[contract_group]:
                for line in pymt_trx.payment_line_ids:
                    for invoice_line in line.move_line_id.move_id.invoice_line_ids:
                        child = invoice_line.contract_id.child_id
                        str_child = ""
                        product_name = invoice_line.product_id.with_context(
                            lang=invoice_line.partner_id.lang
                        ).name
                        if child:
                            # Build a string that looks like (BF Maria-Louisa)
                            str_child = (
                                f"({child.field_office_id.country_id.code + ' ' or None}"
                                f"{child.preferred_name or None})"
                            )
                        text_lines.append(
                            (
                                invoice_line.product_id.id,
                                f"{int(invoice_line.credit)} {product_name} " + str_child,
                            )
                        )
            text_lines.sort(key=lambda a: a[0])

            contract = grouped_payments[contract_group][0]

            data_delivery.sections[0].add_payment(
                customer_number=f"{contract.partner_id.ref:15}",
                mandate_number=contract_group.ref,
                reference=(
                    contract.payment_line_ids[0].date.strftime("%b").capitalize()
                    + " "
                    + contract.payment_line_ids[0].payment_type.capitalize()
                )[:20],
                amount= sum(pymt_trx.amount for pymt_trx in grouped_payments[contract_group]),
                sign_code=beservice.SignCode.COLLECTION,
                payment_date=contract.payment_line_ids[0].date,
                text_lines=text_lines,
            )
        return data_delivery.to_ocr().encode("iso-8859-1"), f"{self.name}.txt"
