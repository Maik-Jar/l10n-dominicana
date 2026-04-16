from . import models
from . import wizard


def pre_init_hook(env):
    """Migra los nombres de facturas dominicanas existentes al formato LATAM.

    Antes de este refactor, las facturas dominicanas guardaban en ``name`` el
    número interno (``"INV/2026/0001"``) y el NCF completo en
    ``l10n_do_fiscal_number`` (``"B0100000001"``). A partir de esta versión,
    ``name`` almacena el número fiscal con el separador LATAM
    (``"B01 00000001"``) y ``l10n_do_fiscal_number`` se calcula a partir de él.

    Este hook reconstruye ``name`` a partir de ``l10n_do_fiscal_number`` y del
    prefijo del tipo de documento, y alinea ``sequence_prefix`` /
    ``sequence_number`` para que el mixin estándar pueda continuar la
    secuencia sin saltos.
    """
    cr = env.cr

    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_move'
          AND column_name = 'l10n_do_fiscal_number'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        UPDATE account_move AS m
        SET
            name = t.doc_code_prefix || ' ' ||
                   SUBSTRING(m.l10n_do_fiscal_number
                             FROM LENGTH(t.doc_code_prefix) + 1),
            sequence_prefix = t.doc_code_prefix || ' ',
            sequence_number = CAST(
                SUBSTRING(m.l10n_do_fiscal_number
                          FROM LENGTH(t.doc_code_prefix) + 1)
                AS INTEGER
            )
        FROM l10n_latam_document_type t
        WHERE m.l10n_latam_document_type_id = t.id
          AND t.doc_code_prefix IS NOT NULL
          AND m.l10n_do_fiscal_number IS NOT NULL
          AND m.l10n_do_fiscal_number <> ''
          AND m.posted_before = TRUE
          AND m.l10n_do_fiscal_number LIKE t.doc_code_prefix || '%'
          AND SUBSTRING(m.l10n_do_fiscal_number
                        FROM LENGTH(t.doc_code_prefix) + 1) ~ '^[0-9]+$'
          AND (m.name IS NULL OR m.name NOT LIKE t.doc_code_prefix || ' %')
        """
    )
