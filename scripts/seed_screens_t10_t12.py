#!/usr/bin/env python3
"""Siapkan dua PO berstatus Disahkan untuk screenshot T-10 dan T-12.

Alur dijalankan lewat XML-RPC dengan akun yang sama seperti di UI:
  - sales.pilar   : membuat PO, baris pesanan, bukti, lalu memeriksa dan meneruskan
  - dirops.pilar  : mengesahkan PO
PO pertama dipakai untuk "Catat Perubahan Pesanan" (T-10), PO kedua untuk
"Batalkan PO Sah" (T-12). Skrip aman dijalankan ulang: setiap kali membuat
dua PO baru dengan tanggal pengiriman yang belum dipakai pelanggan tersebut.

Contoh:
  python scripts/seed_screens_t10_t12.py --db odoo_app
"""

import argparse
import json
import os
import sys
import xmlrpc.client
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seed_demo  # noqa: E402  (generator gambar bukti Telegram)

ORDERS = {
    "change": {
        "address": "Dapur SPPG MBG Cimahi, Jl. Kolonel Masturi No. 12, Cimahi",
        "items": [
            ("Beras Premium", 120, "kg", "Beras premium, kadar air maks. 14%"),
            ("Telur Ayam", 40, "kg", "Telur segar, ukuran seragam"),
            ("Minyak Goreng", 30, "liter", "Kemasan 2 liter"),
            ("Sayur Segar Paket", 60, "paket", "Bayam, wortel, buncis"),
        ],
    },
    "cancel": {
        "address": "Dapur SPPG MBG Cimahi, Jl. Kolonel Masturi No. 12, Cimahi",
        "items": [
            ("Daging Ayam", 50, "kg", "Ayam potong segar, tanpa jeroan"),
            ("Gula Pasir", 25, "kg", "Gula kristal putih"),
            ("Beras Premium", 80, "kg", "Beras premium, kadar air maks. 14%"),
        ],
    },
}


def windows_font(size):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return seed_demo.ImageFont.truetype(path, size)
        except OSError:
            continue
    return seed_demo._original_font(size)


if seed_demo.Image is not None and os.name == "nt":
    seed_demo._original_font = seed_demo.font
    seed_demo.font = windows_font


class Session:
    def __init__(self, url, db, login, password):
        self.db, self.password = db, password
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, login, password, {})
        if not self.uid:
            raise SystemExit(f"Login gagal untuk {login}.")
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object",
                                                allow_none=True)

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password,
                                      model, method, list(args), kwargs)


def ensure_customer(admin):
    name = "Dapur SPPG MBG Cimahi"
    ids = admin.call("pilar.customer", "search", [("customer_name", "=", name)],
                     limit=1)
    if ids:
        return ids[0]
    return admin.call("pilar.customer", "create", {
        "customer_name": name,
        "customer_type": "mbg",
        "telegram_chat_id": "1001001099",
        "contact_name": "Ibu Lestari (Kepala Dapur)",
        "contact_phone": "0813-2200-4517",
        "is_active": True,
    })


def free_dates(admin, customer_id, count):
    used = {
        row["delivery_date"]
        for row in admin.call("pilar.po", "search_read",
                              [("customer_id", "=", customer_id)],
                              fields=["delivery_date"])
        if row["delivery_date"]
    }
    day, found = date.today() + timedelta(days=4), []
    while len(found) < count:
        if day.isoformat() not in used:
            found.append(day.isoformat())
        day += timedelta(days=1)
    return found


def create_approved_po(sales, director, customer_id, key, delivery_date):
    spec = ORDERS[key]
    po_id = sales.call("pilar.po", "create", {
        "customer_id": customer_id,
        "delivery_date": delivery_date,
        "delivery_address": spec["address"],
        "telegram_sender": "Ibu Lestari (Kepala Dapur)",
        "notes": "Pesanan menu makan siang pekan depan.",
        "priority": "1" if key == "change" else "0",
    })
    for name, qty, unit, quality in spec["items"]:
        sales.call("pilar.po.item", "create", {
            "po_id": po_id, "commodity_name": name, "quantity": qty,
            "unit_name": unit, "quality_specification": quality,
        })
    po_name = sales.call("pilar.po", "read", [po_id], fields=["name"])[0]["name"]
    lines = [f"{name} {qty:g} {unit}" for name, qty, unit, _ in spec["items"]]
    image = seed_demo.make_evidence_image(
        po_name, "Dapur SPPG MBG Cimahi", lines, date.today().strftime("%d/%m/%Y 08:15"),
    )
    # Form menampilkan bukti terbaru (received_at desc), jadi foto dibuat
    # paling baru dan pesan teks konfirmasi sedikit lebih awal.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stamp = lambda moment: moment.strftime("%Y-%m-%d %H:%M:%S")  # noqa: E731
    sales.call("pilar.po.evidence", "create", {
        "po_id": po_id,
        "telegram_message_id": f"tg-shot-{po_id}",
        "received_at": stamp(now),
        "sender_telegram_id": "user-1099",
        "message_text": "Pesanan baru: " + ", ".join(lines),
        "file_name": "Bukti Pesanan Telegram",
        "evidence_type": "foto",
        "image": image or False,
    })
    sales.call("pilar.po.evidence", "create", {
        "po_id": po_id,
        "telegram_message_id": f"tg-shot-{po_id}-2",
        "sender_telegram_id": "user-1099",
        "message_text": "Mohon dikirim pagi hari sebelum pukul 07.00.",
        "file_name": "Pesan Konfirmasi Telegram",
        "evidence_type": "teks",
        "received_at": stamp(now - timedelta(minutes=4)),
    })

    sales.call("pilar.po", "action_start_check", [po_id])
    sales.call("pilar.po", "action_validate", [po_id])
    result = sales.call("pilar.po", "read", [po_id],
                        fields=["validation_result", "validation_message"])[0]
    if result["validation_result"] != "lolos":
        raise SystemExit(f"{po_name} tidak lolos validasi:\n{result['validation_message']}")
    sales.call("pilar.po", "action_submit_decision", [po_id])
    director.call("pilar.po", "action_approve", [po_id])
    state = director.call("pilar.po", "read", [po_id], fields=["state"])[0]["state"]
    if state != "disahkan":
        raise SystemExit(f"{po_name} gagal disahkan (status {state}).")
    return {"id": po_id, "name": po_name}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--db", default="odoo_app")
    parser.add_argument("--admin", default="admin")
    parser.add_argument("--admin-password", default="admin")
    parser.add_argument("--sales", default="sales.pilar")
    parser.add_argument("--director", default="dirops.pilar")
    parser.add_argument("--password", default="pilar123")
    parser.add_argument("--out", help="Simpan ID PO ke file JSON ini.")
    args = parser.parse_args()

    admin = Session(args.url, args.db, args.admin, args.admin_password)
    sales = Session(args.url, args.db, args.sales, args.password)
    director = Session(args.url, args.db, args.director, args.password)

    customer_id = ensure_customer(admin)
    dates = free_dates(admin, customer_id, 2)
    seeded = {
        key: create_approved_po(sales, director, customer_id, key, day)
        for key, day in zip(("change", "cancel"), dates)
    }
    for key, po in seeded.items():
        label = "perubahan (T-10)" if key == "change" else "pembatalan (T-12)"
        print(f"{po['name']} (id {po['id']}) Disahkan, untuk {label}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(seeded, handle, indent=2)


if __name__ == "__main__":
    main()
