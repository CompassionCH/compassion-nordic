/** @odoo-module */
/* global document, window */

import { NewSponsorshipWizard } from "@my_compassion/js/my2_new_sponsorship_wizard";

NewSponsorshipWizard.include({
  /**
   * The plan radios (my2_new_sponsorship_plan.xml), when the page has them.
   * @returns {HTMLInputElement[]}
   * @private
   */
  _planRadios() {
    return [
      ...this.el.querySelectorAll('input[name="sponsorship_plus"][required]'),
    ];
  },

  /**
   * Stop the step while no plan is chosen, with the message under the
   * radios, like the payment-mode radios' own.
   *
   * The plan radios are required, but the wizard is submitted by script,
   * which skips the browser's own check. The plan group is scrolled into
   * view below the page header. The server refuses a missing plan as well
   * (new.sponsorship.wizard.finish_sponsorship).
   *
   * @override
   */
  _validateForm() {
    const isValid = this._super(...arguments);
    const radios = this._planRadios();
    if (!radios.length || radios.some((radio) => radio.checked)) {
      return isValid;
    }
    const error = this.el.querySelector(".ns-plan-error");
    if (error) {
      error.classList.remove("d-none");
      for (const radio of radios) {
        radio.setAttribute("aria-describedby", error.id);
      }
    }
    this._scrollBelowHeader(radios[0].closest("fieldset") || radios[0]);
    radios[0].focus({ preventScroll: true });
    return false;
  },

  /**
   * Scroll the element to just below the page header, which stays on top
   * of the page. The page scrolls in a container of its own (#wrapwrap on
   * the website), not in the window, so the nearest scrolling ancestor is
   * moved.
   * @param {HTMLElement} element
   * @private
   */
  _scrollBelowHeader(element) {
    let scroller = element.parentElement;
    while (
      scroller &&
      !(
        /(auto|scroll)/.test(window.getComputedStyle(scroller).overflowY) &&
        scroller.scrollHeight > scroller.clientHeight
      )
    ) {
      scroller = scroller.parentElement;
    }
    scroller = scroller || document.scrollingElement;
    const header =
      document.querySelector("header#top") || document.querySelector("header");
    const headerBottom = header
      ? Math.max(0, header.getBoundingClientRect().bottom)
      : 0;
    scroller.scrollBy({
      top: element.getBoundingClientRect().top - headerBottom - 16,
      behavior: "smooth",
    });
  },

  /**
   * Clear the message once a plan is chosen. Until then the total shows no
   * amount, as the page renders it: neither plan is the sponsor's yet.
   *
   * @override
   */
  _onSponsorshipPlusChange() {
    const radios = this._planRadios();
    if (radios.length) {
      if (!radios.some((radio) => radio.checked)) {
        const total = this.el.querySelector("#ns-total-amount");
        if (total) {
          total.textContent = "–";
        }
        return;
      }
      this.el.querySelector(".ns-plan-error")?.classList.add("d-none");
      for (const radio of radios) {
        radio.removeAttribute("aria-describedby");
      }
    }
    return this._super(...arguments);
  },
});
