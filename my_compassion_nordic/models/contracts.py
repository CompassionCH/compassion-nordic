import logging
import unicodedata

from psycopg2 import OperationalError

from odoo import SUPERUSER_ID, models
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from odoo.addons.payment import utils as payment_utils

from .res_partner import SSN_FORMATS

_logger = logging.getLogger(__name__)


class LetterWriterNotRegistered(Exception):
    """GMC did not register the letter writer. The message is its reason."""


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    def _my2_fixit_configs(self):
        """Supply the Nordic charge-failure emails to the generic engine."""
        first = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_first",
            raise_if_not_found=False,
        )
        final = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_final",
            raise_if_not_found=False,
        )
        if not first or not final:
            return super()._my2_fixit_configs()
        return {"first": first, "final": final}

    def _my2_portal_invitation_config(self):
        config = self.env.ref(
            "my_compassion_nordic.config_portal_invitation",
            raise_if_not_found=False,
        )
        return config or super()._my2_portal_invitation_config()

    # === Post-payment details form ===

    def _my2_details_mandatory(self):
        """The details form is a required step on the Nordic sites: it stays
        due after Stripe supplied the payer's name, so the sponsor still
        confirms who writes to the child and gives their national identity
        number, and it has no "do this later"."""
        self.ensure_one()
        return True

    def _my2_collects_ssn(self):
        """Whether this signup's company asks its sponsors for their SSN.

        Its flag, and a country whose number the form knows how to check
        (SSN_FORMATS), so the flag switched on for any other country cannot
        make the field refuse every value.
        """
        self.ensure_one()
        company = self.company_id.sudo()
        return bool(company.my2_collect_ssn and company.country_id.code in SSN_FORMATS)

    def _my2_ssn_country_code(self):
        """The country whose tax report this signup's gift goes into."""
        self.ensure_one()
        return self.company_id.sudo().country_id.code or ""

    def _my2_details_extra_partner_vals(self, values):
        """Save the payer's national identity number.

        Only what the company actually collects, in the form its tax report
        uses. The controller has already refused a number that is not valid
        for the company's country, so anything arriving here normalises. An
        empty value is left out rather than written: the field is optional,
        and blanking a number already on file would lose it.
        """
        vals = super()._my2_details_extra_partner_vals(values)
        ssn = values.get("social_sec_nr")
        if ssn and self._my2_collects_ssn():
            normalized = self.env["res.partner"]._my2_normalize_ssn(
                ssn, self._my2_ssn_country_code()
            )
            if normalized:
                vals["social_sec_nr"] = normalized
        return vals

    def _my2_apply_details(self, values):
        """Save the details form, keeping the payer and the letter writer apart.

        The payer (partner_id) is who Stripe charged. Their name, once Stripe
        supplied it, is the one the tax report and the gift receipts carry,
        together with the national identity number. The form's name is who
        writes to the child, and the form says to enter someone else's name
        when they do.

        - Stripe reported a name the payer does not carry yet (the payment
          is only authorised, or post-processing has not run): it is applied
          first, so the payer is who Stripe charged before anything below.
        - The payer still carries the placeholder (Stripe sent no name): the
          form's name is the payer's, as on every other site.
        - The form keeps the payer's name (_same_person): written on the
          payer, which corrects a split, the accents a card name lacks, or a
          card name of a single word.
        - Another name: that person becomes the contract's correspondent,
          with the phone number. The payer keeps their name and gets only
          the identity number, and sees the sponsorship in their portal with
          its letters, which they may write (portal_sponsorships
          "all_info"): the letter writer has no email nor account. The
          correspondent change syncs with GMC, so it runs as a queue job
          (_my2_assign_letter_writer): a GMC failure must never turn the
          sponsor's submission into an error page.
        """
        self.ensure_one()
        payer = self.partner_id.sudo()
        firstname = values.get("firstname") or ""
        lastname = values.get("lastname") or ""
        stripe_name = payer.my2_name_placeholder and self._my2_cardholder_name()
        if stripe_name:
            payer._my2_replace_placeholder_name(
                *payment_utils.split_partner_name(stripe_name)
            )
        if payer.my2_name_placeholder:
            return super()._my2_apply_details(values)
        if _same_person(payer.firstname, payer.lastname, firstname, lastname):
            if (payer.firstname or "", payer.lastname or "") != (firstname, lastname):
                payer.write(
                    {"firstname": firstname or False, "lastname": lastname or False}
                )
            return super()._my2_apply_details(values)
        letter_writer = self._my2_create_letter_writer(values)
        payer.portal_sponsorships = "all_info"
        self.sudo().with_delay_sh(
            "_my2_assign_letter_writer",
            letter_writer.id,
            description="Assign the letter writer of a MyCompassion signup",
            identity_key=f"{self._name}._my2_assign_letter_writer.{self.id}",
        )
        return super()._my2_apply_details(
            {**values, "firstname": "", "lastname": "", "phone": ""}
        )

    def _my2_assign_letter_writer(self, letter_writer_id):
        """Make the letter writer the correspondent of this sponsorship.

        Through the ordinary write, which updates the commitment at GMC once
        the sponsorship has one. Before that, GMC still has to know the
        letter writer when the pending sponsorship upsert names them, hence
        the constituent upsert first. A failed upsert does not raise, so the
        job checks it got a GMC id.

        Whatever stops it, a GMC refusal or a call that fails on the way,
        leaves the correspondent as it was and gives staff a to-do on the
        sponsorship (_my2_flag_letter_writer). The job then ends normally
        rather than failing: a failed job is rolled back, to-do included, and
        staff do not watch the job queue. A concurrent update is raised only
        when OCA queue_job runs the job, because it tries the job again. The
        replacement job runner does not, so staff hear of that one too.

        Elevated: queued from the public details form, so the job runs as
        the public user.
        """
        self.ensure_one()
        sponsorship = self.sudo()
        letter_writer = self.env["res.partner"].sudo().browse(letter_writer_id).exists()
        if not letter_writer:
            # Staff merged or deleted the contact before the job ran.
            return "The letter writer no longer exists."
        try:
            with self.env.cr.savepoint():
                if not sponsorship.gmc_commitment_id and not letter_writer.global_id:
                    messages = letter_writer.upsert_constituent()
                    messages.process_messages()
                    if not letter_writer.global_id:
                        raise LetterWriterNotRegistered(
                            "; ".join(filter(None, messages.mapped("failure_reason")))
                        )
                sponsorship.correspondent_id = letter_writer
        except Exception as error:
            if (
                isinstance(error, OperationalError)
                and error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY
                and "queue.job" in self.env
            ):
                raise
            _logger.warning(
                "Letter writer %s is not the correspondent of sponsorship %s.",
                letter_writer.id,
                sponsorship.id,
                exc_info=True,
            )
            sponsorship._my2_flag_letter_writer(letter_writer, error)
            return f"Not assigned, staff have a to-do: {error!r}"
        return True

    def _my2_flag_letter_writer(self, letter_writer, error):
        """Give staff a to-do on this sponsorship: its letter writer could not
        be made its correspondent, so letters still go to the payer.

        Written in the language of the user it is assigned to. Created as
        OdooBot, like the to-dos of scheduled actions: the job runs as the
        public user, who would otherwise sign the email that tells staff
        about it.
        """
        self.ensure_one()
        responsible = self._my2_letter_writer_responsible()
        todo = self.with_user(SUPERUSER_ID).with_context(lang=responsible.lang)
        if isinstance(error, LetterWriterNotRegistered):
            reason = todo.env._(
                "GMC did not register the letter writer. %(reason)s",
                reason=str(error),
            )
        else:
            reason = str(error) or type(error).__name__
        todo.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=todo.env._("Letter writer not assigned"),
            note=todo.env._(
                "%(letter_writer)s, named on the signup form as the person who"
                " writes to the child, could not be made the correspondent of"
                " this sponsorship. The payer stays its correspondent until"
                " you make the change. %(reason)s",
                letter_writer=letter_writer._get_html_link(),
                reason=reason,
            ),
            user_id=responsible.id,
        )

    def _my2_letter_writer_responsible(self):
        """Who gets the to-do about a letter writer GMC did not take: the
        letter responsible of the Compassion settings, or the first active
        administrator when none is set or that user is archived."""
        users = self.env["res.users"].sudo()
        responsible_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sbc_compassion.letter_responsible")
            or ""
        )
        responsible = users.browse(
            int(responsible_id) if responsible_id.isdigit() else 0
        ).exists()
        if responsible.active:
            return responsible
        administrator = users.search(
            [
                ("groups_id", "=", self.env.ref("base.group_system").id),
                ("share", "=", False),
            ],
            order="id",
            limit=1,
        )
        _logger.warning(
            "No active letter responsible in the Compassion settings: the"
            " to-do about the letter writer of sponsorship %s goes to %s.",
            self.id,
            administrator.login,
        )
        return administrator

    def _my2_create_letter_writer(self, values):
        """The correspondent the details form names, as a new contact.

        Never matched against existing partners: the form is public, and
        matching would let whoever holds the token make someone else's
        record the correspondent of this sponsorship. Staff merge real
        duplicates. The letter writer speaks the payer's languages and lives
        in the payer's country until told otherwise.
        """
        self.ensure_one()
        payer = self.partner_id.sudo()
        return (
            self.env["res.partner"]
            .sudo()
            .create(
                {
                    "firstname": values.get("firstname") or False,
                    "lastname": values.get("lastname") or False,
                    "phone": values.get("phone") or False,
                    "lang": payer.lang,
                    "country_id": payer.country_id.id,
                    "spoken_lang_ids": [(6, 0, payer.spoken_lang_ids.ids)],
                }
            )
        )


# Letters NFKD cannot split from their diacritic.
_PLAIN_LETTERS = str.maketrans({"ø": "o", "æ": "ae", "ß": "ss", "-": " "})
# How a card spells the Nordic letters it lacks: Sørensen as SOERENSEN,
# Åsa as AASA, Ærø as AEROE. Folded on both sides, so either spelling of a
# name compares equal.
_DIGRAPHS = (("aa", "a"), ("ae", "a"), ("oe", "o"), ("ue", "u"))


def _name_words(firstname, lastname):
    """A name's words, compared without case, spacing, hyphens or
    diacritics, and with the card spellings of Nordic letters folded."""
    name = f"{firstname or ''} {lastname or ''}".casefold().translate(_PLAIN_LETTERS)
    plain = "".join(
        char
        for char in unicodedata.normalize("NFKD", name)
        if not unicodedata.combining(char)
    )
    for digraph, letter in _DIGRAPHS:
        plain = plain.replace(digraph, letter)
    return plain.split()


def _same_person(payer_firstname, payer_lastname, firstname, lastname):
    """Whether the name typed on the details form is the payer's own.

    The same words, in any order, so a different split or restored accents
    are the same person. Beyond that, only a card name of a single word may
    be completed, and only when it stays the first name ("Pekka" ->
    "Pekka Virtanen"): a longer name that merely contains the payer's
    ("Johan Svensson" -> "Karl Johan Svensson") is as likely a son or a
    namesake, whom the form asks to be entered as the letter writer.
    """
    payer_words = _name_words(payer_firstname, payer_lastname)
    words = _name_words(firstname, lastname)
    if not payer_words or not words:
        return False
    if sorted(payer_words) == sorted(words):
        return True
    return len(payer_words) == 1 and words[0] == payer_words[0]
