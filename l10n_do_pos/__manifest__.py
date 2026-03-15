{
    "name": "Point of Sale - Dominican Republic",
    "summary": "Point of Sale with Dominican NCF Support",
    "author": "iterativo LLC, Indexa",
    "category": "Localization",
    "license": "LGPL-3",
    "website": "https://github.com/odoo-dominicana",
    "version": "19.0.1.0.0",
    "countries": ["do"],
    "depends": [
        "point_of_sale",
        "l10n_do_accounting",
        "l10n_latam_invoice_document",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_do_pos/static/src/xml/receipt_ncf.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
