import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/models/order";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10n_do_ncf = null;
        this.l10n_do_ncf_type = null;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.l10n_do_ncf = this.l10n_do_ncf;
        json.l10n_do_ncf_type = this.l10n_do_ncf_type;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.l10n_do_ncf = json.l10n_do_ncf || null;
        this.l10n_do_ncf_type = json.l10n_do_ncf_type || null;
    },
});
