from odoo import models, api, fields, _


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.model
    def _get_l10n_do_refund_type_selection(self):
        return [
            ("full_refund", _("Full Refund")),
            ("percentage", _("Percentage")),
            ("fixed_amount", _("Amount")),
        ]

    @api.model
    def _get_default_l10n_do_refund_type(self):
        return "full_refund"

    l10n_do_refund_type = fields.Selection(
        selection=_get_l10n_do_refund_type_selection,
        default=_get_default_l10n_do_refund_type,
    )
    l10n_do_percentage = fields.Float("Percentage")
    l10n_do_amount = fields.Float("Amount")
    l10n_do_ecf_modification_code = fields.Selection(
        selection=lambda self: self.env[
            "account.move"
        ]._get_l10n_do_ecf_modification_code(),
        string="e-CF Modification Code",
        copy=False,
    )
    is_ecf_invoice = fields.Boolean(
        string="Is Electronic Invoice",
        compute="_compute_is_ecf_invoice",
    )

    @api.depends("company_id")
    def _compute_is_ecf_invoice(self):
        """La compañía emite e-CF cuando es dominicana y está configurada como emisor."""
        for wiz in self:
            wiz.is_ecf_invoice = (
                wiz.company_id.country_code == "DO"
                and wiz.company_id.l10n_do_ecf_issuer
            )

    @api.depends(
        "l10n_latam_document_type_id", "country_code", "l10n_latam_use_documents"
    )
    def _compute_l10n_latam_manual_document_number(self):
        """Para compañías dominicanas se hereda el flag desde la factura origen."""
        super()._compute_l10n_latam_manual_document_number()
        for rec in self.filtered(
            lambda r: r.move_ids
            and r.l10n_latam_use_documents
            and r.country_code == "DO"
        ):
            move = rec.move_ids[0]
            rec.l10n_latam_manual_document_number = (
                move.l10n_latam_manual_document_number
            )

    def _prepare_default_reversal(self, move):
        """Agrega los campos específicos de la DGII y soporta rectificaciones parciales
        por porcentaje o monto (reemplazando las líneas por una sola línea calculada).
        """
        result = super()._prepare_default_reversal(move)

        if self.country_code != "DO":
            return result

        result.update(
            {
                "l10n_do_ecf_modification_code": self.l10n_do_ecf_modification_code,
                "l10n_do_origin_ncf": move.l10n_do_fiscal_number or move.ref,
                "l10n_do_expense_type": move.l10n_do_expense_type,
                "l10n_do_income_type": move.l10n_do_income_type,
                "invoice_origin": move.name,
            }
        )

        if self.l10n_do_refund_type != "full_refund":
            price_unit = (
                self.l10n_do_amount
                if self.l10n_do_refund_type == "fixed_amount"
                else move.amount_untaxed * (self.l10n_do_percentage / 100)
            )
            result.update(
                {
                    "line_ids": [(5, 0, 0)],
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": self.reason or _("Credit"),
                                "price_unit": price_unit,
                                "quantity": 1,
                            },
                        )
                    ],
                }
            )

        return result
