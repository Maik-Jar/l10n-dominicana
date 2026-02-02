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

### Fixed
- **Actualizado campo `users` → `user_ids` en grupos de seguridad (Odoo 19.0)**
  - El campo para asignar usuarios a grupos cambió de nombre en Odoo 19.0
  - Mantiene la funcionalidad de asignación automática de usuarios a grupos
  - Afecta grupos: `group_l10n_do_fiscal_credit_note`, `group_l10n_do_fiscal_invoice_cancel`, `group_l10n_do_edit_fiscal_partner`, `group_l10n_do_debit_note`
  - Referencias: `odoo/addons/base/models/res_groups.py:17` (código fuente Odoo 19.0)

- **Actualizado XPath en vista de facturas para compatibilidad con Odoo 19.0**
  - Cambiado referencia de `tax_lock_date_message` (removido en 19.0) a `alerts` div
  - Mantiene funcionalidad de mensajes de advertencia para contingencia e-CF y expiración de NCF
  - Referencias: `odoo/addons/account/views/account_move_views.xml:797-799`

- **Actualizado XPath en plantillas de reportes para compatibilidad con Odoo 19.0**
  - Cambiado `hasclass('company_address')` a `[@name='company_address']` en `external_layout_striped`
  - El elemento ya no usa clase CSS sino atributo `name` en Odoo 19.0
  - Mantiene funcionalidad de ocultar dirección de compañía en facturas dominicanas
  - Referencias: `odoo/addons/web/views/report_templates.xml:312`

- **Removido XPath obsoleto de elemento h2 en reporte de factura (Odoo 19.0)**
  - El elemento `<h2>` fue removido del template base `report_invoice_document`
  - Odoo 19.0 ahora usa `layout_document_title` en lugar de h2 para títulos
  - Referencias: `odoo/addons/account/views/report_invoice.xml` (Odoo 19.0)

- **Corregido error "can't adapt type 'NewId'" en _compute_name (Odoo 19.0)**
  - **Corrección final:** Excluidas facturas dominicanas del flujo estándar de secuencias
  - Las facturas DO usan lógica especializada que se ejecuta al confirmar (state='posted')
  - El flujo estándar intentaba establecer secuencias en borradores sin verificar estado
  - Previene `psycopg2.ProgrammingError` al cambiar diario en borradores
  - Referencias: `odoo/addons/account/models/account_move.py:943` (Odoo 19.0)

- **Corregido detección de facturas dominicanas en métodos de secuencia (Odoo 19.0)**
  - Cambiada detección basada en contexto a detección basada en campos del registro
  - Los métodos `_get_sequence_format_param` y `_set_next_sequence` ahora verifican `country_code` y `l10n_latam_use_documents`
  - Previene `AttributeError: 'NoneType' object has no attribute 'groupdict'` al confirmar facturas
  - El contexto `is_l10n_do_seq` se puede perder durante recomputes, causando errores

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
