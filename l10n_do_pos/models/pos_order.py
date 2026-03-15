from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_do_ncf = fields.Char(
        string="NCF",
        readonly=True,
        index="trigram",
        help="Número de Comprobante Fiscal (NCF) asignado",
    )

    l10n_do_ncf_type = fields.Selection(
        selection=[
            ("B01", "Factura de Crédito"),
            ("B02", "Factura de Consumo"),
            ("E31", "e-Factura Crédito"),
            ("E32", "e-Factura Consumo"),
        ],
        string="Tipo de Comprobante",
        readonly=True,
        help="Tipo de documento fiscal dominicano",
    )

    def _is_l10n_do_fiscal_pos(self):
        return self.config_id.l10n_do_fiscal_journal_id

    def _get_l10n_do_document_type(self, partner=None):
        if not self._is_l10n_do_fiscal_pos():
            return None

        config = self.config_id
        journal = config.l10n_do_fiscal_journal_id
        ncf_types = journal._get_journal_ncf_types()

        if not partner:
            partner = self.partner_id or config.l10n_do_default_partner_id

        if not partner:
            return ncf_types.get("consumption", {}).get("doc_type_id")

        tax_payer_type = partner.l10n_do_dgii_tax_payer_type or "non_payer"

        if tax_payer_type == "tax_payer":
            return ncf_types.get("credit", {}).get("doc_type_id")
        else:
            return ncf_types.get("consumption", {}).get("doc_type_id")

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        if self._is_l10n_do_fiscal_pos():
            config = self.config_id
            journal = config.l10n_do_fiscal_journal_id

            vals.update({
                "journal_id": journal.id,
                "l10n_latam_document_type_id": self._get_l10n_do_document_type(
                    self.partner_id
                ),
            })

        return vals

    def _create_invoice(self):
        invoice = super()._create_invoice()

        if invoice and self._is_l10n_do_fiscal_pos():
            invoice_with_context = invoice.with_context(is_l10n_do_seq=True)
            invoice_with_context._set_next_sequence()

            self.l10n_do_ncf = invoice.l10n_do_fiscal_number
            self.l10n_do_ncf_type = invoice.l10n_latam_document_type_id.code

        return invoice

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        return fields + ['l10n_do_ncf', 'l10n_do_ncf_type']
