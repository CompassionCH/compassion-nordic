/** @odoo-module */

import { NewSponsorshipWizard } from "@my_compassion/js/my2_new_sponsorship_wizard";

NewSponsorshipWizard.include({
  /**
   * Stop the step while no plan is chosen.
   *
   * The plan radios are required, but the wizard is submitted by script,
   * which skips the browser's own check, and the field validators of the
   * theme only check one input per field. reportValidity shows the browser's
   * message on the radios. The server refuses a missing plan as well
   * (new.sponsorship.wizard.finish_sponsorship).
   *
   * @override
   */
  _validateForm() {
    const isValid = this._super(...arguments);
    const plan = this.el.querySelector(
      'input[name="sponsorship_plus"][required]',
    );
    if (plan && !plan.checkValidity()) {
      plan.reportValidity();
      return false;
    }
    return isValid;
  },
});
