from werkzeug import urls

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError, AccessError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_do_cancellation_type(self):
        """Retorna los tipos de anulación requeridos por la DGII."""
        return [
            ("01", _("01 - Pre-printed Invoice Impairment")),
            ("02", _("02 - Printing Errors (Pre-printed Invoice)")),
            ("03", _("03 - Defective Printing")),
            ("04", _("04 - Correction of Product Information")),
            ("05", _("05 - Product Change")),
            ("06", _("06 - Product Return")),
            ("07", _("07 - Product Omission")),
            ("08", _("08 - NCF Sequence Errors")),
            ("09", _("09 - For Cessation of Operations")),
            ("10", _("10 - Lossing or Hurting Of Counterfoil")),
        ]

    def _get_l10n_do_ecf_modification_code(self):
        """Retorna los códigos de modificación de e-CF requeridos por la DGII."""
        return [
            ("1", _("01 - Total Cancellation")),
            ("2", _("02 - Text Correction")),
            ("3", _("03 - Amount correction")),
            ("4", _("04 - NCF replacement issued in contingency")),
            ("5", _("05 - Reference Electronic Consumer Invoice")),
        ]

    def _get_l10n_do_income_type(self):
        """Retorna los tipos de ingreso requeridos por la DGII."""
        return [
            ("01", _("01 - Operational Incomes")),
            ("02", _("02 - Financial Incomes")),
            ("03", _("03 - Extraordinary Incomes")),
            ("04", _("04 - Leasing Incomes")),
            ("05", _("05 - Income for Selling Depreciable Assets")),
            ("06", _("06 - Other Incomes")),
        ]

    l10n_do_expense_type = fields.Selection(
        selection=lambda self: self.env["res.partner"]._get_l10n_do_expense_type(),
        string="Cost & Expense Type",
    )

    l10n_do_cancellation_type = fields.Selection(
        selection="_get_l10n_do_cancellation_type",
        string="Cancellation Type",
        copy=False,
    )

    l10n_do_income_type = fields.Selection(
        selection="_get_l10n_do_income_type",
        string="Income Type",
        copy=False,
        default=lambda self: self.env.context.get("l10n_do_income_type", "01"),
    )

    l10n_do_origin_ncf = fields.Char(
        string="Modifies",
    )

    l10n_do_ncf_expiration_date = fields.Date(
        string="Valid until",
    )
    is_ecf_invoice = fields.Boolean(
        compute="_compute_is_ecf_invoice",
        store=True,
    )
    l10n_do_ecf_modification_code = fields.Selection(
        selection="_get_l10n_do_ecf_modification_code",
        string="e-CF Modification Code",
        copy=False,
    )
    l10n_do_ecf_security_code = fields.Char(string="e-CF Security Code", copy=False)
    l10n_do_ecf_sign_date = fields.Datetime(string="e-CF Sign Date", copy=False)
    l10n_do_electronic_stamp = fields.Char(
        string="Electronic Stamp",
        compute="_compute_l10n_do_electronic_stamp",
        store=True,
    )
    l10n_do_company_in_contingency = fields.Boolean(
        string="Company in contingency",
        compute="_compute_company_in_contingency",
    )
    l10n_do_enable_first_sequence = fields.Boolean(
        string="Enable first fiscal sequence",
        compute="_compute_l10n_do_enable_first_sequence",
        help="Technical field that compute if internal generated fiscal sequence "
        "is enabled to be set manually.",
    )
    # Campo computado que se deriva de `name` (formato LATAM "B01 00000001"),
    # removiendo el espacio separador para obtener el NCF completo ("B0100000001").
    l10n_do_fiscal_number = fields.Char(
        "Fiscal Number",
        compute="_compute_l10n_do_fiscal_number",
        store=True,
        index="trigram",
        tracking=True,
        copy=False,
        help="NCF completo derivado del campo name sin el espacio separador.",
    )
    l10n_do_ecf_edi_file = fields.Binary("ECF XML File", copy=False, readonly=True)
    l10n_do_ecf_edi_file_name = fields.Char(
        "ECF XML File Name", copy=False, readonly=True
    )
    # Se fuerza almacenamiento para poder usarlo en los índices únicos SQL.
    l10n_latam_manual_document_number = fields.Boolean(store=True)
    l10n_do_show_expiration_date_msg = fields.Boolean(
        "Show Expiration Date Message",
        compute="_compute_l10n_do_show_expiration_date_msg",
        help="Technical field to hide/show message on invoice header that indicate fiscal number must be input "
        "manually because a new expiration date was set on journal",
    )

    # Índices únicos a nivel de base de datos (Odoo 19.0 usa models.UniqueIndex).
    _unique_l10n_do_fiscal_number_sales = models.UniqueIndex(
        "(l10n_do_fiscal_number, company_id) "
        "WHERE l10n_latam_document_type_id IS NOT NULL "
        "AND move_type NOT IN ('in_invoice', 'in_refund') "
        "AND l10n_do_fiscal_number IS NOT NULL "
        "AND l10n_do_fiscal_number <> ''"
    )
    _unique_l10n_do_fiscal_number_purchase_manual = models.UniqueIndex(
        "(l10n_do_fiscal_number, commercial_partner_id, company_id) "
        "WHERE l10n_latam_document_type_id IS NOT NULL "
        "AND move_type IN ('in_invoice', 'in_refund') "
        "AND l10n_latam_manual_document_number IS TRUE "
        "AND l10n_do_fiscal_number IS NOT NULL "
        "AND l10n_do_fiscal_number <> ''"
    )
    _unique_l10n_do_fiscal_number_purchase_internal = models.UniqueIndex(
        "(l10n_do_fiscal_number, company_id) "
        "WHERE l10n_latam_document_type_id IS NOT NULL "
        "AND move_type IN ('in_invoice', 'in_refund', 'in_receipt') "
        "AND l10n_latam_manual_document_number IS FALSE "
        "AND l10n_do_fiscal_number IS NOT NULL "
        "AND l10n_do_fiscal_number <> ''"
    )

    @api.depends(
        "name",
        "l10n_latam_document_type_id",
        "l10n_latam_use_documents",
        "country_code",
    )
    def _compute_l10n_do_fiscal_number(self):
        """Deriva el NCF completo a partir del campo `name` (formato LATAM).

        El mecanismo estándar de secuencias de Odoo 19.0 asigna `name` con el
        formato `"PREFIX NUMERO"` (p. ej. `"B01 00000001"`). Este método elimina
        el espacio separador para producir el NCF almacenado (`"B0100000001"`).
        """
        for move in self:
            if (
                move.country_code == "DO"
                and move.l10n_latam_use_documents
                and move.l10n_latam_document_type_id
                and move.name
                and move.name != "/"
                and " " in move.name
            ):
                move.l10n_do_fiscal_number = move.name.replace(" ", "", 1)
            else:
                move.l10n_do_fiscal_number = False

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        if name:
            domain = expression.AND(
                [
                    [
                        "|",
                        ("name", operator, name),
                        ("l10n_do_fiscal_number", operator, name),
                    ],
                    domain,
                ]
            )
        return super()._name_search(name, domain, operator, limit, order)

    def _l10n_do_is_new_expiration_date(self):
        self.ensure_one()
        last_invoice = self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("move_type", "=", self.move_type),
                (
                    "l10n_latam_document_type_id",
                    "=",
                    self.l10n_latam_document_type_id.id,
                ),
                ("posted_before", "=", True),
                ("id", "!=", self.id or self._origin.id),
                ("l10n_do_ncf_expiration_date", "!=", False),
            ],
            order="invoice_date desc, id desc",
            limit=1,
        )
        if not last_invoice:
            return False

        return (
            last_invoice.l10n_do_ncf_expiration_date < self.l10n_do_ncf_expiration_date
        )

    @api.depends("l10n_do_ncf_expiration_date", "journal_id")
    def _compute_l10n_do_show_expiration_date_msg(self):
        l10n_do_internal_invoices = self.filtered(
            lambda inv: inv.l10n_latam_use_documents
            and inv.l10n_latam_document_type_id
            and inv.country_code == "DO"
            and not inv.l10n_latam_manual_document_number
            and inv.l10n_do_ncf_expiration_date
        )
        for invoice in l10n_do_internal_invoices:
            invoice.l10n_do_show_expiration_date_msg = (
                invoice._l10n_do_is_new_expiration_date()
            )

        (self - l10n_do_internal_invoices).l10n_do_show_expiration_date_msg = False

    @api.depends(
        "journal_id.l10n_latam_use_documents",
        "l10n_latam_manual_document_number",
        "l10n_latam_document_type_id",
        "company_id",
    )
    def _compute_l10n_do_enable_first_sequence(self):
        """
        Habilita la captura manual del primer número fiscal para comprobantes
        internos cuando no existe ninguna factura previamente publicada del
        mismo tipo de documento.
        """
        l10n_do_internal_invoices = self.filtered(
            lambda inv: inv.l10n_latam_use_documents
            and inv.l10n_latam_document_type_id
            and inv.country_code == "DO"
            and not inv.l10n_latam_manual_document_number
        )
        for invoice in l10n_do_internal_invoices:
            invoice.l10n_do_enable_first_sequence = (
                not bool(
                    self.search_count(
                        [
                            ("company_id", "=", invoice.company_id.id),
                            ("move_type", "=", invoice.move_type),
                            (
                                "l10n_latam_document_type_id",
                                "=",
                                invoice.l10n_latam_document_type_id.id,
                            ),
                            ("posted_before", "=", True),
                            ("id", "!=", invoice.id or invoice._origin.id),
                        ],
                    )
                )
                or invoice.l10n_do_show_expiration_date_msg
            )

        (self - l10n_do_internal_invoices).l10n_do_enable_first_sequence = False

    def _get_l10n_do_amounts(self):
        """
        Prepara los montos fiscales dominicanos usados en reportes y
        facturación electrónica.
        """
        self.ensure_one()

        return self.line_ids.filtered(
            lambda line: line.currency_id == self.currency_id
        )._get_l10n_do_line_amounts()

    @api.depends(
        "company_id",
        "l10n_latam_document_type_id",
    )
    def _compute_is_ecf_invoice(self):
        for invoice in self.filtered(lambda inv: inv.state == "draft"):
            invoice.is_ecf_invoice = (
                invoice.company_id.country_id
                and invoice.country_code == "DO"
                and invoice.l10n_latam_document_type_id
                and invoice.l10n_latam_document_type_id.l10n_do_ncf_type
                and invoice.l10n_latam_document_type_id.l10n_do_ncf_type[:2] == "e-"
            )

    @api.depends("company_id", "company_id.l10n_do_ecf_issuer")
    def _compute_company_in_contingency(self):
        ecf_invoices = self.search(
            [
                ("is_ecf_invoice", "=", True),
            ],
            limit=1,
        ).filtered(lambda i: not i.l10n_latam_manual_document_number)

        # Primero se reinicia el flag en todos los registros
        self.write({"l10n_do_company_in_contingency": False})

        # Luego se activa sólo en facturas en borrador cuando aplica
        for invoice in self.filtered(lambda inv: inv.state == "draft"):
            invoice.l10n_do_company_in_contingency = bool(
                ecf_invoices and not invoice.company_id.l10n_do_ecf_issuer
            )

    @api.depends("l10n_do_ecf_security_code", "l10n_do_ecf_sign_date", "invoice_date")
    def _compute_l10n_do_electronic_stamp(self):
        l10n_do_ecf_invoice = self.filtered(
            lambda i: i.is_ecf_invoice
            and not i.l10n_latam_manual_document_number
            and i.l10n_do_ecf_security_code
            and i.state == "posted"
        )

        for invoice in l10n_do_ecf_invoice:
            if hasattr(invoice.company_id, "l10n_do_ecf_service_env"):
                ecf_service_env = invoice.company_id.l10n_do_ecf_service_env
            else:
                ecf_service_env = "TesteCF"

            doc_code_prefix = invoice.l10n_latam_document_type_id.doc_code_prefix
            is_rfc = (  # Es un Resumen Factura Consumo
                doc_code_prefix == "E32" and invoice.amount_total_signed < 250000
            )

            qr_string = "https://%s.dgii.gov.do/%s/ConsultaTimbre%s?" % (
                "fc" if is_rfc else "ecf",
                ecf_service_env,
                "FC" if is_rfc else "",
            )
            qr_string += "RncEmisor=%s&" % invoice.company_id.vat or ""
            if not is_rfc:
                qr_string += (
                    "RncComprador=%s&" % invoice.commercial_partner_id.vat
                    if invoice.l10n_latam_document_type_id.doc_code_prefix[1:]
                    not in ("43", "47")
                    else ""
                )
            qr_string += "ENCF=%s&" % invoice.l10n_do_fiscal_number or ""
            if not is_rfc:
                qr_string += "FechaEmision=%s&" % (
                    invoice.invoice_date or fields.Date.today()
                ).strftime("%d-%m-%Y")

            total_field = "l10n_do_invoice_total"
            if invoice.currency_id != invoice.company_id.currency_id:
                total_field += "_currency"
            l10n_do_total = invoice._get_l10n_do_amounts()[total_field]

            qr_string += "MontoTotal=%s&" % ("%f" % l10n_do_total).rstrip("0").rstrip(
                "."
            )
            if not is_rfc:
                qr_string += "FechaFirma=%s&" % invoice.l10n_do_ecf_sign_date.strftime(
                    "%d-%m-%Y %H:%M:%S"
                )

            special_chars = " !#$&'()*+,/:;=?@[]\"-.<>\\^_`"
            security_code = "".join(
                (
                    c.replace(c, "%" + c.encode("utf-8").hex()).upper()
                    if c in special_chars
                    else c
                )
                for c in invoice.l10n_do_ecf_security_code or ""
            )
            qr_string += "CodigoSeguridad=%s" % security_code

            invoice.l10n_do_electronic_stamp = urls.url_quote_plus(qr_string, safe="%")

        (self - l10n_do_ecf_invoice).l10n_do_electronic_stamp = False

    @api.constrains(
        "l10n_do_fiscal_number", "partner_id", "company_id", "posted_before"
    )
    def _l10n_do_check_unique_vendor_number(self):
        for rec in self.filtered(
            lambda inv: inv.l10n_do_fiscal_number
            and inv.country_code == "DO"
            and inv.l10n_latam_use_documents
            and inv.is_purchase_document()
            and inv.commercial_partner_id
        ):
            domain = [
                ("move_type", "=", rec.move_type),
                ("l10n_do_fiscal_number", "=", rec.l10n_do_fiscal_number),
                ("company_id", "=", rec.company_id.id),
                ("id", "!=", rec.id),
                ("commercial_partner_id", "=", rec.commercial_partner_id.id),
                ("state", "!=", "cancel"),
            ]
            if rec.search_count(domain):
                raise ValidationError(
                    _(
                        "Vendor bill Fiscal Number must be unique per vendor and company."
                    )
                )

    @api.depends("name", "l10n_latam_document_type_id")
    def _compute_l10n_latam_document_number(self):
        """Para facturas dominicanas se expone el NCF completo (con prefijo y sin espacio)
        en `l10n_latam_document_number`, preservando la experiencia de usuario histórica
        donde el campo visible en la vista muestra el número fiscal tal cual lo captura el
        usuario o lo genera la secuencia.
        """
        l10n_do_recs = self.filtered(
            lambda x: x.country_code == "DO" and x.l10n_latam_use_documents
        )
        for rec in l10n_do_recs:
            if rec.name and rec.name != "/" and " " in rec.name:
                rec.l10n_latam_document_number = rec.name.replace(" ", "", 1)
            else:
                rec.l10n_latam_document_number = False

        super(
            AccountMove, self - l10n_do_recs
        )._compute_l10n_latam_document_number()

    def button_cancel(self):
        fiscal_invoice = self.filtered(
            lambda inv: inv.country_code == "DO"
            and self.move_type[-6:] in ("nvoice", "refund")
            and inv.l10n_latam_use_documents
        )
        not_ecf_fiscal_invoice = fiscal_invoice.filtered(lambda i: not i.is_ecf_invoice)

        if len(fiscal_invoice) > 1:
            raise ValidationError(
                _("You cannot cancel multiple fiscal invoices at a time.")
            )

        if not_ecf_fiscal_invoice and not self.env.user.has_group(
            "l10n_do_accounting.group_l10n_do_fiscal_invoice_cancel"
        ):
            raise AccessError(_("You are not allowed to cancel Fiscal Invoices"))

        if fiscal_invoice and not fiscal_invoice.posted_before:
            raise ValidationError(
                _(
                    "You cannot cancel a fiscal document that has not been posted before."
                )
            )

        if not_ecf_fiscal_invoice and not self.env.context.get(
            "skip_cancel_wizard", False
        ):
            action = (
                self.env.ref("l10n_do_accounting.action_account_move_cancel")
                .sudo()
                .read()[0]
            )
            action["context"] = {"default_move_id": fiscal_invoice.id}
            return action

        if fiscal_invoice:
            fiscal_invoice.button_draft()

        return super(AccountMove, self).button_cancel()

    def action_reverse(self):
        fiscal_invoice = self.filtered(
            lambda inv: inv.country_code == "DO"
            and self.move_type[-6:] in ("nvoice", "refund")
        )
        if fiscal_invoice and not self.env.user.has_group(
            "l10n_do_accounting.group_l10n_do_fiscal_credit_note"
        ):
            raise AccessError(_("You are not allowed to issue Fiscal Credit Notes"))

        return super(AccountMove, self).action_reverse()

    def _inverse_l10n_latam_document_number(self):
        """Convierte el NCF capturado por el usuario al formato LATAM en `name`.

        El usuario ingresa el NCF completo (p. ej. ``"B0100000001"``). Se valida
        mediante ``_format_document_number`` y se guarda en ``name`` con el
        formato LATAM (``"B01 00000001"``) que espera el mixin de secuencias.

        Sólo se actúa sobre facturas dominicanas en borrador que nunca han sido
        posteadas, para evitar pisar el ``name`` generado por la secuencia al
        momento de postear.
        """
        do_moves = self.filtered(
            lambda m: m.country_code == "DO"
            and m.state == "draft"
            and not m.posted_before
        )
        for rec in do_moves.filtered("l10n_latam_document_type_id"):
            if not rec.l10n_latam_document_number:
                rec.name = False
                continue

            document_type_id = rec.l10n_latam_document_type_id
            if document_type_id.l10n_do_ncf_type:
                document_number = document_type_id._format_document_number(
                    rec.l10n_latam_document_number
                )
            else:
                document_number = rec.l10n_latam_document_number

            if rec.l10n_latam_document_number != document_number:
                rec.l10n_latam_document_number = document_number

            prefix = document_type_id.doc_code_prefix or ""
            if prefix and document_number.startswith(prefix):
                rec.name = "%s %s" % (prefix, document_number[len(prefix):])
            else:
                rec.name = document_number

        super(
            AccountMove, self - do_moves
        )._inverse_l10n_latam_document_number()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if not (
            self.journal_id.l10n_latam_use_documents
            and self.journal_id.company_id.country_id == self.env.ref("base.do")
        ):
            return super()._get_l10n_latam_documents_domain()

        internal_types = ["debit_note"]
        if self.move_type in ["out_refund", "in_refund"]:
            internal_types.append("credit_note")
        else:
            internal_types.append("invoice")

        domain = [
            ("internal_type", "in", internal_types),
            ("country_id", "=", self.company_id.country_id.id),
        ]
        ncf_types = self.journal_id._get_journal_ncf_types(
            counterpart_partner=self.partner_id.commercial_partner_id, invoice=self
        )
        domain += [
            "|",
            ("l10n_do_ncf_type", "=", False),
            ("l10n_do_ncf_type", "in", ncf_types),
        ]
        codes = self.journal_id._get_journal_codes()
        if codes:
            domain.append(("code", "in", codes))
        return domain

    @api.constrains("move_type", "l10n_latam_document_type_id")
    def _check_invoice_type_document_type(self):
        l10n_do_invoices = self.filtered(
            lambda inv: inv.country_code == "DO"
            and inv.l10n_latam_use_documents
            and inv.l10n_latam_document_type_id
            and inv.state == "posted"
        )
        for rec in l10n_do_invoices:
            has_vat = bool(rec.partner_id.vat and bool(rec.partner_id.vat.strip()))
            l10n_latam_document_type = rec.l10n_latam_document_type_id
            if not has_vat and (
                rec.amount_untaxed_signed >= 250000
                or (
                    l10n_latam_document_type.is_vat_required
                    and rec.commercial_partner_id.l10n_do_dgii_tax_payer_type
                    != "non_payer"
                )
            ):
                raise ValidationError(
                    _(
                        "A VAT is mandatory for this type of NCF. "
                        "Please set the current VAT of this client"
                    )
                )
        super(AccountMove, self - l10n_do_invoices)._check_invoice_type_document_type()

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if (
            self.company_id.country_id == self.env.ref("base.do")
            and self.l10n_latam_document_type_id
            and self.move_type == "in_invoice"
            and self.partner_id
        ):
            self.l10n_do_expense_type = (
                self.partner_id.l10n_do_expense_type
                if not self.l10n_do_expense_type
                else self.l10n_do_expense_type
            )

        return super(AccountMove, self)._onchange_partner_id()

    @api.depends("l10n_latam_document_type_id", "journal_id")
    def _compute_l10n_latam_manual_document_number(self):
        l10n_do_recs_with_journal_id = self.filtered(
            lambda x: x.journal_id
            and x.journal_id.l10n_latam_use_documents
            and x.l10n_latam_document_type_id
            and x.country_code == "DO"
        )
        for move in l10n_do_recs_with_journal_id:
            move.l10n_latam_manual_document_number = (
                move._is_l10n_do_manual_document_number()
            )

            move.l10n_do_ncf_expiration_date = (
                move.journal_id.l10n_do_document_type_ids.filtered(
                    lambda doc: doc.l10n_latam_document_type_id
                    == move.l10n_latam_document_type_id
                ).l10n_do_ncf_expiration_date
            )

        super(
            AccountMove, self - l10n_do_recs_with_journal_id
        )._compute_l10n_latam_manual_document_number()

    def _is_l10n_do_manual_document_number(self):
        self.ensure_one()

        if self.reversed_entry_id:
            return self.reversed_entry_id.l10n_latam_manual_document_number

        return self.move_type in (
            "in_invoice",
            "in_refund",
        ) and self.l10n_latam_document_type_id.l10n_do_ncf_type not in (
            "minor",
            "e-minor",
            "informal",
            "e-informal",
            "exterior",
            "e-exterior",
        )

    def _get_debit_line_tax(self, debit_date):
        if self.move_type == "out_invoice":
            return (
                self.company_id.account_sale_tax_id
                or self.env.ref("account.%s_tax_18_sale" % self.company_id.id)
                if (debit_date - self.invoice_date).days <= 30
                and self.partner_id.l10n_do_dgii_tax_payer_type != "special"
                else self.env.ref("account.%s_tax_0_sale" % self.company_id.id) or False
            )
        else:
            return self.company_id.account_purchase_tax_id or self.env.ref(
                "account.%s_tax_0_purch" % self.company_id.id
            )

    def _post(self, soft=True):
        res = super()._post(soft)

        l10n_do_invoices = self.filtered(
            lambda inv: inv.company_id.country_id == self.env.ref("base.do")
            and inv.l10n_latam_use_documents
        )

        for invoice in l10n_do_invoices.filtered(
            lambda inv: inv.l10n_latam_document_type_id
        ):
            if not invoice.amount_total:
                raise UserError(_("Fiscal invoice cannot be posted with amount zero."))

        non_payer_type_invoices = l10n_do_invoices.filtered(
            lambda inv: not inv.partner_id.l10n_do_dgii_tax_payer_type
        )
        if non_payer_type_invoices:
            raise ValidationError(_("Fiscal invoices require partner fiscal type"))

        return res

    def _get_starting_sequence(self):
        """Define la secuencia inicial para comprobantes fiscales dominicanos.

        El mecanismo de ``sequence_mixin`` parte de un valor de referencia con el
        formato `"PREFIX 00000000"` para los NCF tradicionales (8 dígitos) o
        `"PREFIX 0000000000"` para los e-CF (10 dígitos).
        """
        if (
            self.journal_id.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.l10n_latam_document_type_id
        ):
            doc_type = self.l10n_latam_document_type_id
            seq_len = (
                10 if str(doc_type.l10n_do_ncf_type or "").startswith("e-") else 8
            )
            return "%s %s" % (doc_type.doc_code_prefix, "0" * seq_len)
        return super()._get_starting_sequence()

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.country_code == "DO":
            return "l10n_do_accounting.report_invoice_document_inherited"
        return super()._get_name_invoice_report()

    def unlink(self):
        if self.filtered(
            lambda inv: inv.is_purchase_document()
            and inv.country_code == "DO"
            and inv.l10n_latam_use_documents
            and inv.posted_before
        ):
            raise UserError(
                _("You cannot delete fiscal invoice which have been posted before")
            )
        return super(AccountMove, self).unlink()

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """Las secuencias fiscales dominicanas son continuas, nunca se reinician."""
        if self.l10n_latam_use_documents and self.company_id.country_id.code == "DO":
            return "never"
        return super()._deduce_sequence_number_reset(name)
