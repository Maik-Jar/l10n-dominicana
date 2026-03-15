import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * Fuerza sincronización con el backend si el POS está configurado con diario fiscal.
     * Garantiza que el NCF se genera antes de mostrar el recibo.
     */
    waitForPushOrder() {
        if (this.config.l10n_do_fiscal_journal_id) {
            return true;
        }
        return super.waitForPushOrder(...arguments);
    },
});
