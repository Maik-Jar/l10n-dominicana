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
        """Obtiene el l10n_latam.document.type correspondiente para una orden POS.

        Determina el tipo de comprobante fiscal (NCF) basándose en el tipo
        de contribuyente del cliente. Los contribuyentes (taxpayer) reciben
        Crédito Fiscal (B01/E31), los demás reciben Consumo (B02/E32).

        :param partner: res.partner opcional. Si no se proporciona, usa el
            partner de la orden o el cliente por defecto de la configuración.
        :return: recordset l10n_latam.document.type o None
        """
        if not self._is_l10n_do_fiscal_pos():
            return None

        config = self.config_id
        journal = config.l10n_do_fiscal_journal_id

        if not partner:
            partner = self.partner_id or config.l10n_do_default_partner_id

        # Determinar el ncf_type según el tipo de contribuyente del partner
        if partner and partner.l10n_do_dgii_tax_payer_type == "taxpayer":
            target_ncf_type = "fiscal"
        else:
            target_ncf_type = "consumer"

        # Obtener los tipos NCF permitidos para este diario/partner
        if partner and partner.l10n_do_dgii_tax_payer_type:
            ncf_types = journal._get_journal_ncf_types(
                counterpart_partner=partner.commercial_partner_id,
            )
        else:
            ncf_types = journal._get_journal_ncf_types()

        # Filtrar para incluir solo el tipo objetivo (y su versión e-CF)
        allowed_ncf_types = [
            t for t in ncf_types
            if t in (target_ncf_type, "e-%s" % target_ncf_type)
        ]

        if not allowed_ncf_types:
            return None

        # Buscar el document type correspondiente usando los prefijos del diario
        codes = journal._get_journal_codes()
        domain = [
            ("country_id.code", "=", "DO"),
            ("l10n_do_ncf_type", "in", allowed_ncf_types),
            ("internal_type", "=", "invoice"),
        ]
        if codes:
            domain.append(("code", "in", codes))

        return self.env["l10n_latam.document.type"].search(domain, limit=1)

    def _generate_l10n_do_ncf(self):
        """Genera NCF para órdenes POS sin factura."""
        self.ensure_one()
        if not self._is_l10n_do_fiscal_pos():
            return

        journal = self.config_id.l10n_do_fiscal_journal_id
        doc_type = self._get_l10n_do_document_type()
        if not doc_type:
            return

        # Obtener secuencia del diario fiscal
        sequence = journal._get_l10n_do_sequence(doc_type)
        if sequence:
            ncf = sequence.next_by_id()
            self.write({
                'l10n_do_ncf': ncf,
                'l10n_do_ncf_type': doc_type.doc_code_prefix,
            })

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        # Generar NCF para órdenes sin factura
        if self._is_l10n_do_fiscal_pos() and not self.to_invoice:
            self._generate_l10n_do_ncf()
        return res

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        if self._is_l10n_do_fiscal_pos():
            config = self.config_id
            journal = config.l10n_do_fiscal_journal_id

            doc_type = self._get_l10n_do_document_type(self.partner_id)
            vals.update({
                "journal_id": journal.id,
                "l10n_latam_document_type_id": doc_type.id if doc_type else False,
            })

        return vals

    def _create_invoice(self, move_vals):
        invoice = super()._create_invoice(move_vals)

        if invoice and self._is_l10n_do_fiscal_pos():
            invoice_with_context = invoice.with_context(is_l10n_do_seq=True)
            invoice_with_context._set_next_sequence()

            self.l10n_do_ncf = invoice.l10n_do_fiscal_number
            self.l10n_do_ncf_type = invoice.l10n_latam_document_type_id.doc_code_prefix

        return invoice
