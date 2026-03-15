from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_do_fiscal_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Diario Fiscal",
        help="Diario contable para documentos fiscales dominicanos",
        domain=[
            ("type", "=", "sale"),
            ("l10n_latam_use_documents", "=", True),
        ],
    )

    l10n_do_default_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente por Defecto (Consumidor)",
        help="Cliente anónimo para ventas B02 sin cliente específico",
    )

    @api.constrains("l10n_do_fiscal_journal_id")
    def _check_l10n_do_fiscal_journal(self):
        for config in self:
            if config.l10n_do_fiscal_journal_id:
                journal = config.l10n_do_fiscal_journal_id
                if journal.type != "sale" or not journal.l10n_latam_use_documents:
                    raise ValidationError(
                        "El diario fiscal debe ser de tipo 'Venta' y tener habilitado 'Usar documentos'."
                    )

    def _get_journal_ncf_types(self):
        if self.l10n_do_fiscal_journal_id:
            return self.l10n_do_fiscal_journal_id._get_journal_ncf_types()
        return []
