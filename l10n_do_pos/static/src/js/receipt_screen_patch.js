import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup(...arguments);
    },

    getReceiptData() {
        const order = this.props.order;
        const receiptData = super.getReceiptData?.() || {};

        if (order.l10n_do_ncf) {
            receiptData.l10n_do_ncf = order.l10n_do_ncf;
            receiptData.l10n_do_ncf_type = order.l10n_do_ncf_type;

            const client = order.partner;
            if (client && client.l10n_do_dgii_tax_payer_type) {
                receiptData.client_rnc = client.vat || '';
            }
        }

        return receiptData;
    },
});
