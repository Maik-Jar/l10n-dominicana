# Changelog

Todos los cambios notables en este módulo serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [19.0.1.0.0] - 2026-01-29

### Changed
- Migración a Odoo 19.0
- Verificación de compatibilidad de funciones SQL (`odoo.tools.sql`)
- Verificación de compatibilidad del método `_get_rates()` para conversión de moneda
- Verificación de vistas XML con atributos `invisible` y `column_invisible`
- **BREAKING:** Removido campo `users` de grupos de seguridad (incompatible con Odoo 19.0)
  - Los usuarios ahora deben asignarse a grupos manualmente desde la interfaz de usuario
  - Afecta grupos: `group_l10n_do_fiscal_credit_note`, `group_l10n_do_fiscal_invoice_cancel`, `group_l10n_do_edit_fiscal_partner`, `group_l10n_do_debit_note`

### Verified
- Funciones SQL compatibles: `index_exists()`, `drop_index()`, `column_exists()`, `create_column()`
- No se encontraron patrones deprecados del ORM (`self._uid`, `self._cr`, `self._context`)
- Vistas XML utilizan sintaxis correcta para Odoo 19.0
- Archivos de seguridad y grupos compatibles
- Suite de tests completa (12 tests unitarios)

### Dependencies
- l10n_do (módulo oficial de Odoo)
- l10n_latam_invoice_document (módulo oficial de Odoo)

### Testing
- 12 tests unitarios disponibles para validación
- Cobertura de flujos fiscales: NCF, ECF, notas de crédito/débito, secuencias
- Pruebas de validación de RNC, tipos de contribuyente, y cálculos de ITBIS

## [17.0.1.0.0] - 2024

### Added
- Implementación base del módulo para Odoo 17.0
- Gestión de comprobantes fiscales (NCF)
- Soporte para facturación electrónica (ECF)
- Tipos de documentos fiscales según normativa DGII
- Secuencias fiscales automáticas
- Validaciones de RNC y cédula
- Notas de crédito y débito fiscales
- Wizards para reversión y cancelación
- Reportes fiscales dominicanos
