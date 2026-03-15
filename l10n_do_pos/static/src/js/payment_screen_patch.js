import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10n_do_ncf_display = null;
    },

    updatePaymentScreenUI() {
        const order = this.pos.get_order();
        if (order && order.l10n_do_ncf) {
            this.l10n_do_ncf_display = {
                ncf: order.l10n_do_ncf,
                ncf_type: order.l10n_do_ncf_type,
            };
        } else {
            this.l10n_do_ncf_display = null;
        }
    },
});
