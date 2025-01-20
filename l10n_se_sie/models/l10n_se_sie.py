import base64
import logging
from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

import odoo
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountSieSerieToJournal(models.TransientModel):
    _name = "account.sie.serie.to.journal"

    name = fields.Char(string="Serie")
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        help="Used to set journal based on Serie of #VER",
    )
    sie_export = fields.Many2one(comodel_name="account.sie")


class AccountSieAccount(models.TransientModel):
    _name = "account.sie.account"
    _description = "SIE Import New Account Line"

    @api.model
    def default_account_type(self):
        # Remplacement de l'ancien user_type par le nouveau account_type
        return "asset_fixed"  # Exemple pour les actifs immobilisés (Fixed Assets)

    wizard_id = fields.Many2one(comodel_name="account.sie", string="Wizard")
    checked = fields.Boolean(string="")
    reconcile = fields.Boolean(string="")
    name = fields.Char(string="Name", required=True, select=True)
    code = fields.Char(string="Code", size=64, required=True)
    type = fields.Selection(
        selection=[
            ("view", "View"),
            ("other", "Regular"),
            ("receivable", "Receivable"),
            ("payable", "Payable"),
            ("liquidity", "Liquidity"),
            ("consolidation", "Consolidation"),
            ("closed", "Closed"),
        ],
        string="Internal Type",
        default="other",
        required=True,
        help="The 'Internal Type' is used for features available on "
        "different types of accounts: view can not have journal items,"
        "consolidation are accounts that can have children accounts for multi-company "
        "consolidations, payable/receivable are for partners accounts "
        "(for debit/credit computations), closed for depreciated accounts.",
    )
    account_type = fields.Selection(
        selection=lambda self: self.env["account.account"]
        ._fields["account_type"]
        .selection,
        string="Account Type",
        required=True,
        default=default_account_type,
        help=(
            "Account Type is used for information purposes, to generate "
            "country-specific legal reports, and set the rules to close a fiscal year "
            "and generate opening entries."
        ),
    )
    parent_id = fields.Many2one(comodel_name="account.account", string="Parent")


class AccountSie(models.TransientModel):
    _name = "account.sie"
    _description = "SIE Import Wizard"
    serie_to_journal_ids = fields.One2many(
        "account.sie.serie.to.journal", "sie_export", string="Series to Journal"
    )
    date_start = fields.Date(string="Date interval")
    date_stop = fields.Date(string="Stop Date")
    fiscalyear_ids = fields.Many2many(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        help="Moves in this fiscal years",
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Journal",
        help="Moves with this type of journals",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Partner",
        help="Moves tied to these partners",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Account",
    )
    account_line_ids = fields.One2many(
        comodel_name="account.sie.account",
        inverse_name="wizard_id",
        string="New Accounts",
    )
    state = fields.Selection(
        [
            ("choose", "choose"),
            ("get", "get"),
        ],
        default="choose",
    )
    data = fields.Binary("File")
    filename = fields.Char(string="Filename")
    show_account_lines = fields.Boolean(string="Show Account Lines")
    move_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        help="All imported account.moves will get this journal",
    )
    company_id = fields.Many2one(comodel_name="res.company", required=True)

    accounts_type = fields.Selection(
        selection=[
            ("view", "View"),
            ("other", "Regular"),
            ("receivable", "Receivable"),
            ("payable", "Payable"),
            ("liquidity", "Liquidity"),
            ("consolidation", "Consolidation"),
            ("closed", "Closed"),
        ],
        string="Internal Type",
        help="The 'Internal Type' is used for features available on "
        "different types of accounts: view can not have journal items, "
        "consolidation are accounts that can have children accounts for multi-company "
        "consolidations, payable/receivable are for partners accounts "
        "(for debit/credit computations), closed for depreciated accounts.",
    )
    accounts_user_type = fields.Selection(
        selection=lambda self: self.env["account.account"]
        ._fields["account_type"]
        .selection,
        string="Account Type",
        help="Account Type is used for information purpose, to generate "
        "country-specific legal reports, and set the rules to close a fiscal year "
        "and generate opening entries.",
    )

    accounts_parent_id = fields.Many2one(
        comodel_name="account.account", string="Parent"
    )

    @api.model
    def cleanse_with_fire(self, data):
        data = base64.decodestring(data or "").decode("cp437")
        text_list = []
        # Clean away empty lines and carriage return.
        # Ceterum censeo Bill Gates esse delendam.
        for line in data.split("\n"):
            line = line.strip()
            if line:
                text_list.append(line)
        data = self.read_file(text_list)
        return data

    def check_import_file(self, data=None):
        self.ensure_one()
        if data or self.data:  # IMPORT TRIGGERED
            checked = True
            data = data or self.cleanse_with_fire(self.data)
            missing_accounts = self.env["account.account"].check__missing_accounts(
                self._import_accounts(data)
            )
            if len(missing_accounts) > 0:
                checked = False
            return checked

    def create_accounts(self):
        self.ensure_one()
        for line in self.account_line_ids:
            self.env["account.account"].create(
                {
                    "company_id": self.company_id.id,
                    "name": line.name,
                    "code": line.code,
                    "account_type": line.account_type,
                    "root_id": line.parent_id and line.parent_id.id or None,
                    "reconcile": line.reconcile,
                }
            )
        self.account_line_ids = None
        self.show_account_lines = False

    @api.model
    def read_line(self, line, i=0):
        # TRANS 2013 {} 15887 "" "" 0
        res = []
        field = ""
        citation = False
        escaped = False
        while i < len(line):
            if escaped:
                field += line[i]
                escaped = False
            elif line[i] == "\\":
                escaped = True
            else:
                if citation:
                    if line[i] == '"':
                        citation = False
                        if field == "" and "#TRANS" in line:
                            # just an empty "",
                            # we still need that in order to determine
                            # which value was in which index.
                            field = "Empty Citation"
                    else:
                        field += line[i]
                elif line[i] == "{":
                    _temp_line, i = self.read_line(line, i + 1)
                    res.append(_temp_line)
                elif line[i] == "}":
                    if field:
                        res.append(field)
                    return res, i
                elif line[i] in (" ", "\t"):
                    if field:
                        res.append(field)
                        field = ""
                elif line[i] == '"':
                    citation = True
                else:
                    field += line[i]
            i += 1
        if field:
            res.append(field)
        return res

    @api.model
    def read_file(self, text_list, i=0):
        res = []
        last_line = None
        while i < len(text_list):
            _logger.debug(i)
            if text_list[i] == "{":
                line, i = self.read_file(text_list, i + 1)
                last_line["lines"] = line
            elif text_list[i] == "}":
                return res, i
            else:
                line = self.read_line(text_list[i])
                last_line = {}
                for x in range(len(line)):
                    if x == 0:
                        last_line["label"] = line[x]
                    else:
                        last_line[x] = line[x]
                res.append(last_line)
            i += 1
        return res

    def get_missing_accounts(self):
        if self.data:
            data = self.cleanse_with_fire(self.data)

            if not self.check_import_file(data):
                missing_accounts = self.env["account.account"].check__missing_accounts(
                    self._import_accounts(data)
                )
                for account in missing_accounts:
                    # Determine account type based on the code
                    account_type = next(
                        (
                            sel[0]
                            for sel in self.env["account.account"]
                            ._fields["account_type"]
                            .selection
                            if sel[0] == account[0]
                        ),
                        "asset_fixed",  # Default to Fixed Assets if not found
                    )

                    be_reconcilable = account_type in [
                        "asset_receivable",
                        "liability_payable",
                    ]

                    # Check if account line already exists
                    sie_account_id = self.env["account.sie.account"].search(
                        [("code", "=", account[0]), ("wizard_id", "=", self.id)],
                        limit=1,
                    )
                    if not sie_account_id:
                        self.write(
                            {
                                "account_line_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "code": account[0],
                                            "name": account[1],
                                            "account_type": account_type,
                                            "reconcile": be_reconcilable,
                                        },
                                    )
                                ]
                            }
                        )
                    else:
                        self.write(
                            {
                                "account_line_ids": [
                                    (
                                        1,
                                        sie_account_id.id,
                                        {
                                            "code": account[0],
                                            "name": account[1],
                                            "reconcile": be_reconcilable,
                                        },
                                    )
                                ]
                            }
                        )

    def send_form(self):
        self.ensure_one()

        if self.data:  # IMPORT TRIGGERED
            if not self.move_journal_id:
                raise UserError(_("Please select a journal"))
            data = self.cleanse_with_fire(self.data)
            if not self.check_import_file(data):
                missing_accounts = self.env["account.account"].check__missing_accounts(
                    self._import_accounts(data)
                )
                formatstring = ""
                for account in missing_accounts:
                    formatstring += account[0] + ": " + account[1] + "\n"
                    # self._create_missing_accounts(account[0], account[1])

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Missing Accounts",
                        "message": "Some accounts are missing",
                        "sticky": False,
                    },
                }
            move_ids = self._import_ver(data)
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "account.action_move_journal_line"
            )
            action["res_ids"] = move_ids
            return action
        else:
            search = [("state", "=", "posted")]
            if self.date_start:
                search.append(("date", ">=", self.date_start))
            if self.date_stop:
                search.append(("date", "<=", self.date_stop))
            if self.company_id:
                search.append(("company_id", "=", self.company_id.id))
            if self.journal_ids:
                search.append(("journal_id", "in", [j.id for j in self.journal_ids]))
            if self.partner_ids:
                search.append(("partner_id", "in", [p.id for p in self.partner_ids]))
            move_ids = self.env["account.move"].search(search)
            self.fiscalyear_ids = (
                self.env["account.fiscal.year"]
                .search(
                    [
                        ("company_id", "=", self.company_id.id),
                        (
                            "date_from",
                            "<=",
                            move_ids.sorted("date", reverse=True)[0].date,
                        ),
                        (
                            "date_to",
                            ">=",
                            move_ids.sorted("date", reverse=False)[0].date,
                        ),
                    ]
                )
                .sorted("date_from", reverse=False)
            )
            if self.account_ids:
                accounts = [
                    move_line.move_id.id
                    for move_line in self.env["account.move.line"].search(
                        [("account_id", "in", [a.id for a in self.account_ids])]
                    )
                ]
                move_ids = move_ids.filtered(lambda r: r.id in accounts)

            self.write(
                {
                    "state": "get",
                    "data": base64.encodebytes(self.make_sie(move_ids)),
                    "filename": "filename.se",
                }
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.sie",
            "view_mode": "form",
            "view_type": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }

    def make_sie(self, move_ids):
        def generate_residual_balance_data(acc_balances, fiscal_year_code):
            res = ""
            for account_code, balance in acc_balances.items():
                bsacc = self.env["account.account"].search(
                    [
                        ("code", "=", account_code),
                        ("include_initial_balance", "=", True),
                        ("company_id", "=", self.company_id.id),
                    ]
                )
                if bsacc:
                    res += (
                        f"#UB {fiscal_year_code} {account_code} "
                        f"{round(balance, 2)}\n"
                    )
                else:
                    res += (
                        f"#RES {fiscal_year_code} {account_code} "
                        f"{round(balance, 2)}\n"
                    )
            return res

        if not self:
            raise UserError(
                _("There are no entries for this selection, please do another")
            )

        res = self._generate_header()
        res += self.fiscalyear_ids.generate_fiscalyear_sie()
        res += "\n".join(move_ids.mapped("line_ids.account_id.sie_name"))

        acc_balances = defaultdict(float)
        res += self.fiscalyear_ids.generate_initial_balance_data(acc_balances)

        if len(self.fiscalyear_ids) == 1:
            pl_res = self.env["account.move.line"].read_group(
                domain=[
                    ("move_id.state", "=", "posted"),
                    ("date", "<", self.fiscalyear_ids[0].date_from),
                    (
                        "date",
                        ">=",
                        self.fiscalyear_ids[0].date_from - relativedelta(years=1),
                    ),
                    ("account_id.include_initial_balance", "=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                fields=["account_id", "balance"],
                groupby=["account_id"],
            )
            for i in pl_res:
                acc = self.env["account.account"].browse(i["account_id"][0]).code
                res += f"#RES -1 {acc} {round(i['balance'], 2)}\n"

        prev_fy_position = False
        fiscal_year_position = 0
        for move in move_ids.sorted(lambda r: r.date, reverse=False):
            fiscal_year_position = (
                0
                if len(self.fiscalyear_ids) == 1
                else self.fiscalyear_ids.get_fiscal_year_position(
                    self.fiscalyear_ids.filtered(
                        lambda x, m=move: x.date_from <= m.date <= x.date_to
                    )
                )
            )
            if prev_fy_position and prev_fy_position != fiscal_year_position:
                res += generate_residual_balance_data(acc_balances, prev_fy_position)
            prev_fy_position = fiscal_year_position
            res += move.generate_sie_data(acc_balances)

        res += generate_residual_balance_data(acc_balances, fiscal_year_position)
        return res.encode("cp437", "xmlcharrefreplace")

    def _generate_header(self):
        company = self.company_id
        user = self.env["res.users"].browse(self._context["uid"])
        return (
            "#FLAGGA 0\n"
            f'#PROGRAM "Odoo" {odoo.service.common.exp_version()["server_serie"]}\n'
            "#FORMAT PC8\n"
            f"#GEN {fields.Date.today().strftime('%Y%m%d')}\n"
            "#SIETYP 4\n"
            f'#FNAMN "{company.name}"\n'
            f"#ORGNR {company.company_registry}\n"
            f'#ADRESS "{user.display_name}" "{company.street}" "{company.zip} '
            f'{company.city}" "{company.phone}"\n'
            f"#KPTYP {company.kptyp or 'BAS2015'}\n"
        )

    @api.model
    def export_sie(self, move_ids):
        if len(self) < 1:
            sie_form = self.create({})
        else:
            sie_form = self[0]
        _logger.info("export: %s" % move_ids)
        sie_form.write(
            {
                "state": "get",
                "data": base64.b64encode(sie_form.make_sie(move_ids)),
                "filename": "filename.se",
            }
        )
        view = self.env.ref("l10n_se_sie.wizard_account_sie", False)
        _logger.info(
            "view %s sie_form %s %s %s",
            (
                view,
                sie_form,
                sie_form.data,
                base64.b64encode(sie_form.make_sie(move_ids)),
            ),
        )
        return {
            "name": _("SIE-export"),
            "type": "ir.actions.act_window",
            "res_model": "account.sie",
            "view_mode": "form",
            "view_type": "form",
            "res_id": sie_form.id,
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
        }

    # if narration is null, return empty string instead of parsing to False
    def fix_empty(self, narration):
        if narration:
            return narration
        else:
            return ""

    def import_sie(self):
        sie_form = self[0]
        raise UserError(sie_form.data)

    def _import_accounts(self, data):
        accounts = []
        for line in data:
            if line["label"] == "#KONTO":
                _logger.debug(line)
                # During the process of reading the example file we sometimes
                # don't have a value in index 2. This happens when a line in the
                # example file looks like this ' #KONTO 3019 "" '
                if len(line) < 3:
                    accounts.append((line[1], ""))
                else:
                    accounts.append((line[1], line[2]))
        return accounts

    def _import_ver(self, data):
        self.ensure_one()
        journal_types = []
        move_ids = []
        ib_move_id = False
        move_line_obj = self.env["account.move.line"].with_context(
            check_move_validity=False
        )

        for line in data:
            if line["label"] == "#VER":
                list_date = line.get(3)
                list_ref = f"{line.get(1, ' ')} {line.get(2, ' ')} {line.get(4, ' ')}"
                move_journal_id = self.move_journal_id.id

                serie_to_journal_lines = self.serie_to_journal_ids.filtered(
                    lambda x, _line=line: x.name == _line.get(1)
                )
                if len(serie_to_journal_lines) > 1:
                    raise UserError(
                        "There are two lines with the same series.\n"
                        + "\n".join(
                            f"{line.name} = {line.journal_id.name}"
                            for line in serie_to_journal_lines
                        )
                        + "\nPlease remove one of the lines."
                    )
                elif len(serie_to_journal_lines) == 1:
                    move_journal_id = serie_to_journal_lines.journal_id.id

                ver_id = self.env["account.move"].create(
                    {
                        "journal_id": move_journal_id,
                        "date": f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}",
                        "ref": list_ref,
                    }
                )
                move_ids.append(ver_id.id)

                for subline in line.get("lines", []):
                    if subline["label"] == "#TRANS":
                        trans_code = subline[1]
                        trans_balance = subline[3]
                        trans_date = subline.get(4)
                        trans_name = subline.get(5)
                        code = self.env["account.account"].search(
                            [
                                ("code", "=", trans_code),
                                ("company_id", "=", self.company_id.id),
                            ],
                            limit=1,
                        )

                        if code.account_type in ["income", "income_other"]:
                            journal_types.append(
                                "sale" if float(trans_balance) > 0.0 else "sale_refund"
                            )
                        elif code.account_type == "asset_cash":
                            journal_types.append("bank")
                        elif code.account_type == "liability_credit_card":
                            journal_types.append("cash")
                        elif (
                            code.account_type == "expense"
                            or "asset" in code.account_type
                        ):
                            journal_types.append(
                                "purchase"
                                if float(trans_balance) > 0.0
                                else "purchase_refund"
                            )

                        _logger.debug(f"\naccount_id :{code}\nbalance: {trans_balance}")

                        formated_date = (
                            f"{trans_date[:4]}-" f"{trans_date[4:6]}{trans_date[6:]}"
                            if trans_date and trans_date != "Empty Citation"
                            else ver_id.date
                        )
                        trans_name = (
                            "" if trans_name == "Empty Citation" else trans_name
                        )

                        line_vals = {
                            "account_id": code.id,
                            "credit": float(trans_balance) < 0
                            and float(trans_balance) * -1
                            or 0.0,
                            "debit": float(trans_balance) > 0
                            and float(trans_balance)
                            or 0.0,
                            "date": formated_date,
                            "name": trans_name,
                            "move_id": ver_id.id,
                        }

                        trans_id = move_line_obj.create(line_vals)
                        trans_id._compute_analytic_distribution()

                        tax_line_id = (
                            self.env["account.tax"]
                            .search([("name", "=ilike", trans_name)], limit=1)
                            .id
                        )
                        if tax_line_id:
                            trans_id.tax_line_id = tax_line_id

            elif line["label"] == "#IB":
                year_num = int(line.get(1))
                first_date_of_year = f"{datetime.today().year + year_num}-01-01"
                ib_account = self.env["account.account"].search(
                    [
                        ("code", "=", line.get(2)),
                        ("company_id", "=", self.company_id.id),
                    ]
                )
                ib_amount = line.get(3)
                ib_move_journal_id = self.move_journal_id.id

                if not ib_move_id:
                    ib_move_id = self.env["account.move"].create(
                        {
                            "journal_id": ib_move_journal_id,
                            "date": first_date_of_year,
                            "ref": "IB",
                            "is_incoming_balance_move": True,
                        }
                    )

                line_vals = {
                    "account_id": ib_account.id,
                    "credit": float(ib_amount) < 0 and float(ib_amount) * -1 or 0.0,
                    "debit": float(ib_amount) > 0 and float(ib_amount) or 0.0,
                    "date": first_date_of_year,
                    "name": "#IB",
                    "move_id": ib_move_id.id,
                }

                move_line_obj.create(line_vals)

        opposite_account = self.env["account.account"].search(
            [("company_id", "=", self.company_id.id), ("code", "=", "1930")]
        )
        move_balance = (
            sum(line.balance for line in ib_move_id.line_ids) if ib_move_id else 0
        )

        if move_balance != 0:
            line_vals = {
                "account_id": opposite_account.id,
                "credit": float(move_balance) > 0 and float(move_balance) or 0.0,
                "debit": float(move_balance) < 0 and float(move_balance) * -1 or 0.0,
                "date": first_date_of_year,
                "name": "#IB",
                "move_id": ib_move_id.id,
            }
            move_line_obj.create(line_vals)

        return move_ids
