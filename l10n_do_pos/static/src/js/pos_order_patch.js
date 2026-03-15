import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10n_do_ncf = this.l10n_do_ncf || null;
        this.l10n_do_ncf_type = this.l10n_do_ncf_type || null;
    },
});
