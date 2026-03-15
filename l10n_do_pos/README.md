# l10n_do_pos - Point of Sale con NCF Dominicano

Módulo para agregar soporte de Números de Comprobante Fiscal (NCF) en Point of Sale de Odoo 19.0 para República Dominicana.

## Características (Fase 1)

✅ NCF tradicionales (B01 Crédito, B02 Consumo)
✅ Detección automática de tipo según RNC cliente
✅ Integración con secuencias fiscales (l10n_do_accounting)
✅ Recibo fiscal con NCF, tipo y RNC cliente
✅ Sin duplicación de lógica de l10n_do_accounting

## Requisitos Previos

1. **l10n_do_accounting** instalado con diarios fiscales configurados
2. **Diario contable** de venta con "Usar documentos" habilitado
3. **Localización dominicana** activada

## Pasos de Configuración

### 1. Instalar el Módulo

```bash
# En Odoo, ir a: Apps > Buscar "l10n_do_pos" > Instalar
```

### 2. Configurar POS (Essential)

**Ruta:** Punto de Venta > Configuración > Configuraciones de Punto de Venta

Para cada configuración de POS:

1. **Configuración Fiscal Dominicana**
   - **Diario Fiscal:** Seleccionar el diario de venta con documentos habilitados
   - **Cliente por Defecto:** Seleccionar partner para ventas B02 (consumo) sin cliente específico
     - Este partner debe tener tipo de contribuyente = "non_payer"

### 3. Validar Facturación

Cuando se complete una orden en POS:

- Sistema detecta automáticamente:
  - **B01** si cliente tiene RNC (tax_payer)
  - **B02** si cliente no tiene RNC o es anónimo

- Se genera `account.move` con NCF
- Se asigna automáticamente numero fiscal
- El recibo muestra: **NCF, Tipo, RNC Cliente**

## Estructura del Recibo

El recibo POS mostrará la siguiente sección fiscal:

```
═══════════════════════════════════
COMPROBANTE FISCAL (NCF)
NCF: 101010000001230
Tipo: B02 (Factura de Consumo)
RNC Cliente: 12345678901
═══════════════════════════════════
```

## Configuración de Partner (Clientes)

**Para clientes que son contribuyentes (factura B01):**
- Campo `vat` (RNC): Debe tener 9 dígitos
- Campo `l10n_do_dgii_tax_payer_type` = `tax_payer`

**Para consumidores (factura B02):**
- Campo `l10n_do_dgii_tax_payer_type` = `non_payer`
- O campo `vat` vacío

**Cliente anónimo/por defecto:**
- Crear un partner sin RNC
- Tipo de contribuyente = `non_payer`
- Asignar en "Cliente por Defecto" en configuración de POS

## Troubleshooting

### El recibo no muestra NCF

1. ✓ Verificar que el módulo esté instalado
   ```
   Punto de Venta > Aplicaciones > l10n_do_pos instalado
   ```

2. ✓ Verificar configuración de POS
   ```
   Punto de Venta > Configuración > [Tu POS]
   - Debe tener "Diario Fiscal" asignado
   - Debe tener "Cliente por Defecto" para B02
   ```

3. ✓ Verificar diario fiscal
   ```
   Contabilidad > Configuración > Diarios
   - El diario debe estar de tipo "Venta"
   - Debe tener "Usar documentos" ✓
   - Debe tener tipos de documento (B01, B02) configurados
   ```

4. ✓ Completar una orden y facturar

5. ✓ Revisar la orden en POS
   ```
   Punto de Venta > Órdenes
   - Columna "NCF" debe mostrar el número asignado
   ```

### El NCF no se asigna

- Verificar que el diario fiscal tiene tipos B01/B02 configurados
- Verificar que l10n_do_accounting genera secuencias (test en facturas regulares)
- Revisar logs: `Contabilidad > Facturación > Secuencias Fiscales`

## Datos Técnicos

**Campos agregados:**

- `pos.config.l10n_do_fiscal_journal_id` - Diario para documentos fiscales
- `pos.config.l10n_do_default_partner_id` - Cliente predeterminado para B02
- `pos.order.l10n_do_ncf` - Número de comprobante fiscal (readonly)
- `pos.order.l10n_do_ncf_type` - Tipo de comprobante (B01/B02)

**Ruta de datos:**

1. Usuario completa orden en POS
2. Al facturar, `pos.order._create_invoice()` genera `account.move`
3. Se llama `account.move._set_next_sequence()` con contexto `is_l10n_do_seq=True`
4. Se asigna `l10n_do_fiscal_number` del account.move a `pos.order.l10n_do_ncf`
5. Recibo OWL renderiza `order.l10n_do_ncf` y `order.l10n_do_ncf_type`

## Fase 2 (Futuro)

🔲 e-Facturas (E31, E32) con firma digital DGII
🔲 Código QR con URL de validación DGII
🔲 Modo contingencia cuando DGII no está disponible
🔲 Devoluciones con Notas de Crédito (NC)

## Soporta

- Odoo 19.0
- República Dominicana
- Normas DGII para NCF tradicionales (Resolución 07-18)

## Licencia

LGPL-3

## Autor

iterativo LLC, Indexa
