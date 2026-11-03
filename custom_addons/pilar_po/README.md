# pilar_po — Validasi & Persetujuan Purchase Order

Modul Odoo 17 untuk Milestone 4: validasi dan persetujuan Purchase Order (PO)
PT Pilar Agrosinergi Nusantara. Modul merealisasikan proses bisnis PB-03 dan
kebutuhan FR-01 sampai FR-15: pencatatan PO, pemeriksaan kelengkapan otomatis,
pengembalian dan perbaikan PO, persetujuan berbatas waktu, pengingat/eskalasi,
ringkasan PO tertunda, penyampaian PO sah ke Operasional/Purchasing/Keuangan/Driver,
serta pembatalan dengan jejak audit.

## Struktur

```
pilar_po/
├── __manifest__.py
├── models/                 # pilar.po, versi, item, bukti, validasi, keputusan, audit, config
├── security/               # group peran + ACL
├── views/                  # tree, form, search, kanban, graph, pivot, calendar, menu
├── data/                   # konfigurasi awal + sequence nomor PO (noupdate)
├── demo/                   # pelanggan dan PO contoh (hanya DB demo)
├── report/                 # QWeb PDF ringkasan PO tertunda & salinan PO sah
├── tests/                  # test alur status, validasi, izin, dan versi
└── static/description/     # ikon aplikasi
```

## Model Data

| Entitas ERD | Model Odoo |
|---|---|
| `purchase_order` | `pilar.po` |
| `po_version` | `pilar.po.version` |
| `po_item` | `pilar.po.item` |
| `transaction_evidence` | `pilar.po.evidence` |
| `approval_decision` | `pilar.approval.decision` |
| `AuditLog` | `pilar.audit.log` |
| `system_config` | `pilar.po.config` |
| `po_validation` | `pilar.po.validation` |
| `Customer` | `pilar.customer` |

## Alur Status

```
Bukti Diterima → Dalam Pemeriksaan → Menunggu Keputusan → Disahkan
                        │                     │
                        ├→ Dikembalikan ──────┤
                        │   (perbaikan)       ├→ Ditunda → Disahkan
                        └─────────────────────┴→ Dibatalkan
```

## Peran

Group tersedia di kategori **Operations**: Staff Sales, Director of Operational,
Head of Operational, Purchasing, Director of Finance, Head of Driver,
Executive Director, dan Administrator Modul. ACL diatur di
`security/ir.model.access.csv`.

Akun demo yang dibuat `scripts/seed_demo.py` (kata sandi `pilar123`):
`sales.pilar`, `dirops.pilar`, `exec.pilar`, `finance.pilar`, `ops.pilar`,
`purchasing.pilar`, dan `driver.pilar`.

## Perintah

Jalankan dari root repository template:

```bash
# Install
docker compose run --rm web odoo -d odoo_app -i pilar_po --stop-after-init

# Upgrade setelah mengubah model/view/security
docker compose run --rm web odoo -d odoo_app -u pilar_po --stop-after-init

# Test
docker compose run --rm web odoo -d odoo_test -i pilar_po --test-enable \
  --test-tags /pilar_po --stop-after-init --without-demo=all
```

Data contoh dapat diisi lewat XML-RPC (setelah Odoo berjalan):

```bash
python3 scripts/seed_demo.py --db odoo_app
```

Data referensi wajib (konfigurasi dan sequence) berada di `data/` sebagai XML;
contoh ringkas berada di `demo/`. `scripts/seed_demo.py` hanya generator tambahan
untuk data presentasi/screenshot, bukan pengganti data XML tim.

## Data Presentasi

Database tanpa data demo akan menampilkan layar kosong. Jalankan
`scripts/seed_demo.py` untuk mengisi seluruh layar dengan 23 PO contoh yang
mencakup ketujuh status, bukti transaksi, keputusan, validasi, dan audit.

Tabel screen mockup dan tangkapan layar tidak disimpan di repository ini; kedua
artefak tersebut merupakan lampiran dokumen milestone.
