from odoo import fields, models


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
        """
        if not self._is_l10n_do_fiscal_pos():
            return None

        config = self.config_id
        journal = config.l10n_do_fiscal_journal_id

        if not partner:
            partner = self.partner_id or config.l10n_do_default_partner_id

        if partner and partner.l10n_do_dgii_tax_payer_type == "taxpayer":
            target_ncf_type = "fiscal"
        else:
            target_ncf_type = "consumer"

        if partner and partner.l10n_do_dgii_tax_payer_type:
            ncf_types = journal._get_journal_ncf_types(
                counterpart_partner=partner.commercial_partner_id,
            )
        else:
            ncf_types = journal._get_journal_ncf_types()

        allowed_ncf_types = [
            t for t in ncf_types if t in (target_ncf_type, "e-%s" % target_ncf_type)
        ]

        if not allowed_ncf_types:
            return None

        codes = journal._get_journal_codes()
        domain = [
            ("country_id.code", "=", "DO"),
            ("l10n_do_ncf_type", "in", allowed_ncf_types),
            ("internal_type", "=", "invoice"),
        ]
        if codes:
            domain.append(("code", "in", codes))

        return self.env["l10n_latam.document.type"].search(domain, limit=1)

    def _prepare_invoice_vals(self):
        """Inyecta el diario fiscal y tipo de documento en la factura del POS."""
        vals = super()._prepare_invoice_vals()

        if self._is_l10n_do_fiscal_pos():
            journal = self.config_id.l10n_do_fiscal_journal_id
            doc_type = self._get_l10n_do_document_type(self.partner_id)
            vals.update({
                "journal_id": journal.id,
                "l10n_latam_document_type_id": doc_type.id if doc_type else False,
            })

        return vals

    def _generate_pos_order_invoice(self):
        """Genera la factura del POS y captura el NCF generado por la secuencia.

        El flujo estándar de ``point_of_sale`` crea la factura en borrador y
        luego invoca ``_post()``, que dispara el ``sequence_mixin`` y asigna el
        NCF en ``name``. Una vez posteada la factura, se copia el NCF completo
        (campo computado ``l10n_do_fiscal_number``) a la orden POS para que
        quede disponible en el recibo y en reportes.
        """
        invoice = super()._generate_pos_order_invoice()

        do_orders = self.filtered(lambda o: o._is_l10n_do_fiscal_pos())
        for order in do_orders:
            move = order.account_move
            if move and move.l10n_do_fiscal_number:
                order.write({
                    "l10n_do_ncf": move.l10n_do_fiscal_number,
                    "l10n_do_ncf_type": (
                        move.l10n_latam_document_type_id.doc_code_prefix
                    ),
                })

        return invoice
