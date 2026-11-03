{
    "name": "Pilar PO Center",
    "version": "17.0.1.1.0",
    "summary": "Modul Validasi dan Persetujuan Purchase Order PT Pilar Agrosinergi Nusantara",
    "description": """
Modul simulasi Milestone 4 untuk validasi dan persetujuan Purchase Order (PO).
Mencakup antrean pemeriksaan Staff Sales, persetujuan Director of Operational,
pengembalian PO, riwayat audit, ringkasan PO tertunda, serta daftar PO sah untuk
operasional, purchasing, keuangan, dan pengiriman.
    """,
    "author": "IF3141",
    "maintainer": "Kelompok 08 - K01",
    "website": "https://github.com/fariswirakusuma/IF3141-odoo-K01-G08",
    "category": "Operations/Purchase",
    "license": "LGPL-3",
    "depends": ["base", "mail", "web"],
    # Urutan penting: security dulu (group dipakai ACL dan view), lalu view,
    # menu, data awal, dan terakhir report.
    "data": [
        "security/po_groups.xml",
        "security/ir.model.access.csv",
        "views/po_order_views.xml",
        "views/po_config_views.xml",
        "views/po_customer_views.xml",
        "views/po_menus.xml",
        "data/po_config_data.xml",
        "report/po_reports.xml",
    ],
    # Hanya dimuat jika DB dibuat tanpa --without-demo.
    "demo": ["demo/demo.xml"],
    "installable": True,
    "application": True,
}
