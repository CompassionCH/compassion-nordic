/** @odoo-module */
/* global Stripe, console, document */

import { StripeOptions } from "@payment_stripe/js/stripe_options";
import paymentForm from "@payment/js/payment_form";

/**
 * Payment Element options that make Stripe collect the payer's name for
 * every payment method. It only asks for some on its own ('auto').
 *
 * @param {Object} options - The options core passes to elements.create.
 * @returns {Object}
 */
function withBillingName(options = {}) {
  return {
    ...options,
    fields: {
      ...options.fields,
      billingDetails: { ...options.fields?.billingDetails, name: "always" },
    },
  };
}

paymentForm.include({
  /**
   * Make Stripe's Payment Element ask a fast-checkout payer for their name.
   *
   * The server flags the inline form values with my2_ask_billing_name
   * (payment.provider._stripe_get_inline_form_values). Core builds the
   * element options inside its own _prepareInlineForm, so the Elements
   * group it is about to create is wrapped to add the option to the
   * payment element. Should anything here fail, core's form is left as it
   * is: the details form after payment asks the name anyway.
   *
   * @override method from @payment_stripe/js/payment_form
   */
  async _prepareInlineForm(
    providerId,
    providerCode,
    paymentOptionId,
    paymentMethodCode,
    flow,
  ) {
    if (
      providerCode === "stripe" &&
      flow !== "token" &&
      !this.stripeElements?.[paymentOptionId]
    ) {
      try {
        this._my2AskStripeForName();
      } catch (error) {
        console.warn("Could not make Stripe ask for the payer name", error);
      }
    }
    return this._super(...arguments);
  },

  /**
   * Wrap the Stripe instance core is about to use, once, when the
   * selected option's inline form asks for the payer's name.
   *
   * @private
   * @returns {void}
   */
  _my2AskStripeForName() {
    const radio = document.querySelector(
      'input[name="o_payment_radio"]:checked',
    );
    const container = this._getInlineForm(radio)?.querySelector(
      '[name="o_stripe_element_container"]',
    );
    if (!container) {
      return;
    }
    const values = JSON.parse(container.dataset.stripeInlineFormValues);
    if (!values.my2_ask_billing_name) {
      return;
    }
    // Created exactly as core would, which then reuses it (??=).
    this.stripeJS ??= Stripe(
      values.publishable_key,
      new StripeOptions()._prepareStripeOptions(container.dataset),
    );
    if (this.stripeJS.my2AsksBillingName) {
      return;
    }
    const createElements = this.stripeJS.elements.bind(this.stripeJS);
    // Stripe.js exposes elements as a getter without a setter: assigning
    // it throws, so the property is redefined on the instance instead.
    Object.defineProperty(this.stripeJS, "elements", {
      configurable: true,
      writable: true,
      value: (elementsOptions) => {
        const elements = createElements(elementsOptions);
        const create = elements.create.bind(elements);
        elements.create = (type, options) =>
          create(type, type === "payment" ? withBillingName(options) : options);
        return elements;
      },
    });
    this.stripeJS.my2AsksBillingName = true;
  },
});
