import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/store";

patch(PosStore.prototype, {
    async load_server_data() {
        await super.load_server_data(...arguments);

        for (const config of this.pos_configs) {
            if (!config.l10n_do_fiscal_journal_id) {
                config.l10n_do_fiscal_journal_id = false;
            }
            if (!config.l10n_do_default_partner_id) {
                config.l10n_do_default_partner_id = false;
            }
        }
    },
});
