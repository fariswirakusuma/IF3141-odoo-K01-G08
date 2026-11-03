#!/usr/bin/env python3
"""Seed data demo untuk modul pilar_po melalui XML-RPC Odoo."""

import argparse
import base64
import io
from datetime import datetime, timedelta, timezone

import xmlrpc.client

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None


STATUS_LABEL = {
    "bukti_diterima": "Bukti Diterima",
    "dalam_pemeriksaan": "Dalam Pemeriksaan",
    "dikembalikan": "Dikembalikan",
    "menunggu_keputusan": "Menunggu Keputusan",
    "ditunda": "Ditunda",
    "disahkan": "Disahkan",
    "dibatalkan": "Dibatalkan",
}

COMMODITIES = {
    "beras": ("Beras Premium", "kg"),
    "minyak": ("Minyak Goreng", "liter"),
    "telur": ("Telur Ayam", "kg"),
    "sayur": ("Sayur Segar Paket", "paket"),
    "daging": ("Daging Ayam", "kg"),
    "gula": ("Gula Pasir", "kg"),
}


def font(size):
    for path in (
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_evidence_image(po_name, customer, lines, stamp):
    if Image is None:
        return False
    width, height = 620, 900
    img = Image.new("RGB", (width, height), (229, 235, 238))
    draw = ImageDraw.Draw(img)

    # Telegram header
    draw.rectangle([0, 0, width, 88], fill=(81, 125, 162))
    draw.text((18, 24), "<", font=font(34), fill="white")
    draw.ellipse([54, 18, 116, 80], fill=(122, 167, 199))
    draw.text((78, 33), "P", font=font(28), fill="white")
    draw.text((132, 18), "Grup Pesanan PT Pilar", font=font(24), fill="white")
    draw.text((132, 52), "12 anggota", font=font(16), fill=(212, 230, 242))

    # Incoming order bubble
    y0 = 112
    line_height = 32
    bubble_h = 132 + line_height * len(lines)
    draw.rounded_rectangle([24, y0, width - 24, y0 + bubble_h], radius=14,
                           fill=(255, 255, 255))
    draw.text((44, y0 + 14), "Admin Grup Pesanan", font=font(18),
              fill=(58, 149, 213))
    draw.text((44, y0 + 42), "Pesanan baru", font=font(23), fill=(15, 23, 42))
    draw.text((44, y0 + 76), po_name, font=font(21), fill=(37, 99, 235))
    draw.text((44, y0 + 106), f"Pelanggan: {customer}", font=font(18),
              fill=(51, 65, 85))
    y = y0 + 138
    draw.text((44, y), f"Rincian pesanan  ·  {stamp}", font=font(17),
              fill=(100, 116, 139))
    y += 30
    for line in lines:
        draw.text((52, y), f"•  {line}", font=font(19), fill=(30, 41, 59))
        y += line_height
    draw.text((width - 96, y0 + bubble_h - 26), stamp[-5:], font=font(15),
              fill=(148, 163, 184))

    # Photo attachment bubble
    py = y0 + bubble_h + 12
    photo_h = 286
    draw.rounded_rectangle([24, py, width - 24, py + photo_h], radius=14,
                           fill=(255, 255, 255))
    draw.rounded_rectangle([44, py + 16, 218, py + 232], radius=6,
                           fill=(241, 245, 249), outline=(203, 213, 225))
    draw.rectangle([58, py + 30, 204, py + 62], fill=(30, 64, 175))
    draw.text((70, py + 38), "NOTA PESANAN", font=font(15), fill="white")
    draw.text((58, py + 78), "PT Pilar Agrosinergi", font=font(14),
              fill=(30, 41, 59))
    draw.text((58, py + 100), f"No. {po_name.split('/')[-1]}", font=font(13),
              fill=(100, 116, 139))
    draw.line([(58, py + 124), (204, py + 124)], fill=(203, 213, 225), width=2)
    ry = py + 138
    for idx, line in enumerate(lines[:4]):
        short = line if len(line) <= 20 else line[:19] + "…"
        draw.text((58, ry), short, font=font(12), fill=(51, 65, 85))
        draw.text((186, ry), f"{idx + 1}x", font=font(12), fill=(100, 116, 139))
        ry += 20
    draw.text((58, py + 222), "Terima kasih", font=font(12), fill=(148, 163, 184))
    draw.text((244, py + 22), "Foto nota pesanan", font=font(19),
              fill=(30, 41, 59))
    draw.text((244, py + 52), "Mohon dicek kelengkapannya.", font=font(16),
              fill=(100, 116, 139))
    draw.text((244, py + 78), "Dikirim via Telegram", font=font(15),
              fill=(148, 163, 184))
    draw.text((width - 96, py + photo_h - 26), stamp[-5:], font=font(15),
              fill=(148, 163, 184))

    # Outgoing reply bubble
    oy = py + photo_h + 12
    draw.rounded_rectangle([210, oy, width - 24, oy + 76], radius=14,
                           fill=(239, 253, 222))
    draw.text((230, oy + 14), "Siap, segera kami periksa ya, Pak.", font=font(17),
              fill=(30, 41, 59))
    draw.text((width - 90, oy + 48), stamp[-5:], font=font(15),
              fill=(120, 160, 90))

    # Message input bar
    draw.rectangle([0, height - 56, width, height], fill=(242, 245, 247))
    draw.rounded_rectangle([18, height - 44, width - 58, height - 12], radius=16,
                           fill="white", outline=(218, 224, 230))
    draw.text((34, height - 38), "Pesan", font=font(17), fill=(148, 163, 184))
    draw.ellipse([width - 48, height - 44, width - 16, height - 12],
                 fill=(81, 125, 162))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class Odoo:
    def __init__(self, url, db, user, password):
        self.url = url.rstrip("/")
        self.db = db
        self.password = password
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            raise SystemExit("Autentikasi Odoo gagal.")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(self.db, self.uid, self.password, model, method,
                                      list(args), kwargs)

    def search(self, model, domain, **kwargs):
        return self.call(model, "search", domain, **kwargs)

    def read(self, model, ids, fields):
        return self.call(model, "read", ids, fields)

    def create(self, model, vals):
        return self.call(model, "create", vals)

    def write(self, model, ids, vals):
        return self.call(model, "write", ids, vals)

    def xmlid(self, module, name):
        rows = self.call(
            "ir.model.data", "search_read",
            [("module", "=", module), ("name", "=", name)],
            fields=["res_id", "model"], limit=1,
        )
        if not rows:
            raise SystemExit(f"XML ID tidak ditemukan: {module}.{name}")
        return rows[0]["res_id"]


def dt(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


def ensure_company(odoo):
    company_ids = odoo.search("res.company", [], limit=1)
    if company_ids:
        odoo.write("res.company", company_ids, {
            "name": "PT Pilar Agrosinergi Nusantara",
            "logo": False,
        })


def ensure_locale(odoo):
    lang_ids = odoo.search("res.lang", [("code", "=", "en_US")], limit=1)
    if lang_ids:
        odoo.write("res.lang", lang_ids, {
            "date_format": "%d/%m/%Y",
            "time_format": "%H:%M:%S",
        })


def ensure_user(odoo, login, name, group_xmlid, base_group):
    existing = odoo.search("res.users", [("login", "=", login)], limit=1)
    group_id = odoo.xmlid("pilar_po", group_xmlid) if group_xmlid else False
    groups = [base_group] + ([group_id] if group_id else [])
    vals = {
        "name": name,
        "login": login,
        "password": "pilar123",
        "email": f"{login}@pilar.example.com",
        "groups_id": [(6, 0, groups)],
    }
    if existing:
        odoo.write("res.users", existing, vals)
        return existing[0]
    return odoo.create("res.users", vals)


def ensure_customer(odoo, name, segment, chat_id, contact, phone):
    existing = odoo.search("pilar.customer", [("customer_name", "=", name)], limit=1)
    vals = {
        "customer_name": name,
        "customer_type": segment,
        "telegram_chat_id": chat_id,
        "contact_name": contact,
        "contact_phone": phone,
        "is_active": True,
    }
    if existing:
        odoo.write("pilar.customer", existing, vals)
        return existing[0]
    return odoo.create("pilar.customer", vals)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--db", default="odoo_app")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--reset", action="store_true",
                        help="Hapus seluruh PO demo sebelum membuat ulang.")
    args = parser.parse_args()

    odoo = Odoo(args.url, args.db, args.user, args.password)
    ensure_company(odoo)
    ensure_locale(odoo)

    base_group = odoo.xmlid("base", "group_user")

    users = {
        "sales": ensure_user(odoo, "sales.pilar", "Rani Staff Sales",
                             "group_po_sales", base_group),
        "director": ensure_user(odoo, "dirops.pilar", "Bima Director of Operational",
                                "group_po_director", base_group),
        "executive": ensure_user(odoo, "exec.pilar", "Sari Executive Director",
                                 "group_po_executive", base_group),
        "finance": ensure_user(odoo, "finance.pilar", "Dewi Director of Finance",
                               "group_po_finance", base_group),
        "ops": ensure_user(odoo, "ops.pilar", "Agus Head of Operational",
                           "group_po_operations", base_group),
        "purchasing": ensure_user(odoo, "purchasing.pilar", "Tono Purchasing",
                                  "group_po_purchasing", base_group),
        "driver": ensure_user(odoo, "driver.pilar", "Joko Head of Driver",
                              "group_po_driver", base_group),
    }

    customers = {
        "berkah": ensure_customer(
            odoo, "Toko Berkah Jaya", "mbg", "1001001001",
            "Admin Berkah", "0812-1111-2201",
        ),
        "sumber": ensure_customer(
            odoo, "CV Sumber Makmur", "horeca", "1001001002",
            "Admin Sumber", "0812-1111-2202",
        ),
        "bunda": ensure_customer(
            odoo, "Katering Sehat Bunda", "mbg", "1001001003",
            "Admin Bunda", "0812-1111-2203",
        ),
        "nusantara": ensure_customer(
            odoo, "PT Nusantara Retail", "mbg", "1001001004",
            "Admin Nusantara", "0812-1111-2204",
        ),
        "tani": ensure_customer(
            odoo, "Koperasi Tani Makmur", "horeca", "1001001005",
            "Admin Tani", "0812-1111-2205",
        ),
        "siti": ensure_customer(
            odoo, "Warung Bu Siti", "mbg", "1001001006",
            "Bu Siti", "0812-1111-2206",
        ),
    }

    config_ids = odoo.search("pilar.po.config", [("active", "=", True)], limit=1)
    if config_ids:
        config_id = config_ids[0]
    else:
        config_id = odoo.create("pilar.po.config", {"name": "Konfigurasi PO"})

    if args.reset:
        ids = odoo.search("pilar.po", [])
        if ids:
            odoo.call("pilar.po", "unlink", ids)
            print(f"Menghapus {len(ids)} PO lama.")

    if odoo.search("pilar.po", [], limit=1):
        print("Data PO sudah ada. Gunakan --reset untuk membuat ulang.")
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    specs = [
        {
            "key": "berkah", "segment": "mbg", "state": "bukti_diterima",
            "age_hours": 2, "priority": "0",
            "address": "Jl. Cihampelas No. 88, Bandung",
            "lines": [("beras", 60), ("minyak", 24), ("telur", 15)],
        },
        {
            "key": "sumber", "segment": "horeca", "state": "dalam_pemeriksaan",
            "age_hours": 9, "priority": "1",
            "address": "Jl. Gatot Subroto No. 21, Cimahi",
            "lines": [("daging", 40), ("sayur", 25), ("minyak", 30)],
            "checker": "ops",
        },
        {
            "key": "bunda", "segment": "mbg", "state": "dikembalikan",
            "age_hours": 26, "priority": "0",
            "address": "Jl. Sukajadi No. 5, Bandung",
            "lines": [("beras", 45), ("telur", 12)],
            "checker": "ops", "return_reason": "bukti_tidak_terbaca",
            "return_note": "Foto bukti buram. Mohon unggah ulang bukti yang terbaca.",
        },
        {
            "key": "nusantara", "segment": "mbg", "state": "menunggu_keputusan",
            "age_hours": 8, "priority": "1",
            "address": "Jl. Ahmad Yani No. 45, Bekasi",
            "lines": [("beras", 120), ("gula", 40), ("minyak", 60)],
            "checker": "ops", "decision_stage_hours": 6,
        },
        {
            "key": "tani", "segment": "horeca", "state": "menunggu_keputusan",
            "age_hours": 52, "priority": "1",
            "address": "Jl. Otista No. 17, Garut",
            "lines": [("sayur", 50), ("daging", 35)],
            "checker": "ops", "decision_stage_hours": 50,
        },
        {
            "key": "siti", "segment": "mbg", "state": "ditunda",
            "age_hours": 30, "priority": "0",
            "address": "Jl. Dago No. 3, Bandung",
            "lines": [("minyak", 10), ("gula", 8)],
            "checker": "ops", "decider": "director",
            "postpone_reason": "Menunggu konfirmasi harga dari pemasok.",
        },
        {
            "key": "berkah", "segment": "mbg", "state": "disahkan",
            "age_hours": 72, "priority": "0", "delivery_offset": 2,
            "address": "Jl. Cihampelas No. 88, Bandung",
            "lines": [("beras", 80), ("telur", 20)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 48,
        },
        {
            "key": "sumber", "segment": "horeca", "state": "disahkan",
            "age_hours": 96, "priority": "1", "delivery_offset": 4,
            "address": "Jl. Gatot Subroto No. 21, Cimahi",
            "lines": [("daging", 55), ("sayur", 30), ("beras", 40)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 72,
        },
        {
            "key": "nusantara", "segment": "mbg", "state": "disahkan",
            "age_hours": 120, "priority": "0", "delivery_offset": 7,
            "address": "Jl. Ahmad Yani No. 45, Bekasi",
            "lines": [("gula", 25), ("minyak", 35)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 96,
        },
        {
            "key": "siti", "segment": "mbg", "state": "dibatalkan",
            "age_hours": 48, "priority": "0",
            "address": "Jl. Dago No. 3, Bandung",
            "lines": [("beras", 15)],
            "cancel_reason": "Pelanggan membatalkan pesanan secara sepihak.",
        },
        {
            "key": "bunda", "segment": "horeca", "state": "dalam_pemeriksaan",
            "age_hours": 1, "priority": "0",
            "address": "Jl. Sukajadi No. 5, Bandung",
            "lines": [("sayur", 18), ("telur", 9)],
        },
        {
            "key": "tani", "segment": "mbg", "state": "dikembalikan",
            "age_hours": 14, "priority": "0",
            "address": "Jl. Otista No. 17, Garut",
            "lines": [("beras", 30), ("gula", 12)],
            "checker": "ops", "return_reason": "data_tidak_lengkap",
            "return_note": "Alamat pengiriman belum lengkap.",
        },
        {
            "key": "nusantara", "segment": "mbg", "state": "bukti_diterima",
            "age_hours": 1, "priority": "1", "delivery_offset": 3,
            "address": "Jl. Ahmad Yani No. 45, Bekasi",
            "lines": [("beras", 25), ("minyak", 10)],
        },
        {
            "key": "tani", "segment": "horeca", "state": "bukti_diterima",
            "age_hours": 3, "priority": "0", "delivery_offset": 4,
            "address": "Jl. Otista No. 17, Garut",
            "lines": [("telur", 14), ("sayur", 20)],
        },
        {
            "key": "siti", "segment": "mbg", "state": "dalam_pemeriksaan",
            "age_hours": 5, "priority": "0", "delivery_offset": 2,
            "address": "Jl. Dago No. 3, Bandung",
            "lines": [("gula", 18), ("beras", 22)],
            "checker": "ops",
        },
        {
            "key": "berkah", "segment": "mbg", "state": "dikembalikan",
            "age_hours": 18, "priority": "0", "delivery_offset": 2,
            "address": "Jl. Cihampelas No. 88, Bandung",
            "lines": [("beras", 70), ("telur", 18)],
            "checker": "ops", "return_reason": "data_tidak_sesuai",
            "return_note": "Jumlah beras tidak sesuai dengan nota pesanan.",
        },
        {
            "key": "berkah", "segment": "mbg", "state": "menunggu_keputusan",
            "age_hours": 10, "priority": "1", "delivery_offset": 1,
            "address": "Jl. Cihampelas No. 88, Bandung",
            "lines": [("beras", 95), ("gula", 30)],
            "checker": "ops", "decision_stage_hours": 8,
        },
        {
            "key": "bunda", "segment": "mbg", "state": "menunggu_keputusan",
            "age_hours": 35, "priority": "0", "delivery_offset": 3,
            "address": "Jl. Sukajadi No. 5, Bandung",
            "lines": [("sayur", 40), ("daging", 25)],
            "checker": "ops", "decision_stage_hours": 32,
        },
        {
            "key": "nusantara", "segment": "mbg", "state": "ditunda",
            "age_hours": 40, "priority": "0", "delivery_offset": 5,
            "address": "Jl. Ahmad Yani No. 45, Bekasi",
            "lines": [("minyak", 45), ("gula", 20)],
            "checker": "ops", "decider": "director",
            "decision_stage_hours": 36,
            "postpone_reason": "Armada pada tanggal pengiriman sudah penuh.",
        },
        {
            "key": "tani", "segment": "horeca", "state": "disahkan",
            "age_hours": 60, "priority": "0", "delivery_offset": 6,
            "address": "Jl. Otista No. 17, Garut",
            "lines": [("beras", 55), ("telur", 25)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 40,
        },
        {
            "key": "siti", "segment": "mbg", "state": "disahkan",
            "age_hours": 80, "priority": "1", "delivery_offset": 8,
            "address": "Jl. Dago No. 3, Bandung",
            "lines": [("minyak", 18), ("gula", 12)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 60,
        },
        {
            "key": "bunda", "segment": "mbg", "state": "disahkan",
            "age_hours": 100, "priority": "0", "delivery_offset": 1,
            "address": "Jl. Sukajadi No. 5, Bandung",
            "lines": [("daging", 30), ("sayur", 35)],
            "checker": "ops", "decider": "director", "decision_stage_hours": 80,
        },
        {
            "key": "tani", "segment": "mbg", "state": "dibatalkan",
            "age_hours": 20, "priority": "0", "delivery_offset": 2,
            "address": "Jl. Otista No. 17, Garut",
            "lines": [("beras", 10)],
            "cancel_reason": "Dapur pelanggan tutup sementara.",
        },
    ]

    customer_names = {}
    for key, customer_id in customers.items():
        customer_names[key] = odoo.read(
            "pilar.customer", [customer_id], ["customer_name"]
        )[0]["customer_name"]

    created = []
    for index, spec in enumerate(specs, start=1):
        age = timedelta(hours=spec["age_hours"])
        submitted = now - age
        decision_age = timedelta(hours=spec.get("decision_stage_hours", spec["age_hours"]))
        stage_started = now - decision_age
        decision_time = stage_started
        if spec["state"] in ("disahkan", "ditunda"):
            decision_time = max(stage_started, submitted + timedelta(hours=3))
            stage_started = decision_time

        delivery_date = now + timedelta(days=spec.get("delivery_offset", 2))
        item_vals = []
        evidence_lines = []
        for key, qty in spec["lines"]:
            commodity_name, unit_name = COMMODITIES[key]
            item_vals.append({
                "commodity_name": commodity_name,
                "quantity": qty,
                "unit_name": unit_name,
                "quality_specification": "Kualitas premium, kemasan bersih",
            })
            evidence_lines.append(f"{commodity_name} {qty} {unit_name}")

        image = make_evidence_image(
            f"PO/{submitted.year}/{submitted.month:02d}/{index:04d}",
            customer_names[spec["key"]],
            evidence_lines,
            submitted.strftime("%d %b %Y %H:%M"),
        )

        vals = {
            "customer_id": customers[spec["key"]],
            "config_id": config_id,
            "created_by": users["sales"],
            "delivery_address": spec["address"],
            "delivery_date": delivery_date.strftime("%Y-%m-%d"),
            "telegram_sender": "Admin Grup Pesanan",
            "notes": "Pesanan diterima melalui grup Telegram resmi.",
            "state": spec["state"],
            "priority": spec["priority"],
            "submitted_at": dt(submitted),
            "stage_started_at": dt(stage_started),
        }
        if spec["state"] == "dikembalikan":
            vals["return_reason"] = spec["return_reason"]
            vals["return_note"] = spec["return_note"]
        if spec["state"] == "ditunda":
            vals["postpone_reason"] = spec["postpone_reason"]
        if spec["state"] == "dibatalkan":
            vals["cancel_reason"] = spec["cancel_reason"]
        if spec.get("checker"):
            vals["checked_by"] = users[spec["checker"]]
            vals["checked_at"] = dt(submitted + timedelta(hours=1))

        po_id = odoo.create("pilar.po", vals)
        created.append(po_id)

        po = odoo.read("pilar.po", [po_id], ["name", "state"])[0]

        version_ids = odoo.search("pilar.po.version", [
            ("po_id", "=", po_id), ("is_current", "=", True),
        ], limit=1)
        if not version_ids:
            raise SystemExit(f"Versi PO tidak terbentuk untuk {po['name']}.")
        version_id = version_ids[0]

        for item in item_vals:
            odoo.create("pilar.po.item", dict(item, po_id=po_id, version_id=version_id))

        odoo.create("pilar.po.evidence", {
            "po_id": po_id,
            "telegram_message_id": f"tg-{po_id}-{index}",
            "sender_telegram_id": f"user-{1000 + index}",
            "message_text": "Pesanan baru: " + ", ".join(evidence_lines),
            "file_path": f"/telegram/{po['name'].replace('/', '-')}.png",
            "file_name": "Bukti Pesanan Telegram",
            "evidence_type": "foto",
            "received_at": dt(submitted),
            "image": image or False,
        })

        if spec["state"] in ("dikembalikan", "menunggu_keputusan", "ditunda", "disahkan"):
            if spec["state"] == "dikembalikan":
                result = "bermasalah"
                details = f"- {spec['return_note']}"
            else:
                result = "lolos"
                details = (
                    "Seluruh kolom wajib terisi dan sesuai. PO siap diteruskan."
                )
            odoo.create("pilar.po.validation", {
                "version_id": version_id,
                "config_id": config_id,
                "validation_result": result,
                "validation_details": details,
                "validated_at": dt(submitted + timedelta(hours=1)),
            })
            odoo.write("pilar.po", [po_id], {
                "checked_by": users.get(spec.get("checker", "ops")),
                "checked_at": dt(submitted + timedelta(hours=1)),
            })

        if spec["state"] in ("disahkan", "ditunda"):
            odoo.create("pilar.approval.decision", {
                "po_id": po_id,
                "user_id": users.get(spec.get("decider", "director")),
                "decision_type": "setuju" if spec["state"] == "disahkan" else "tunda",
                "reason": (
                    "PO sah menjadi dasar operasional, tagihan, dan pengiriman."
                    if spec["state"] == "disahkan" else spec["postpone_reason"]
                ),
                "decision_at": dt(decision_time),
            })
        elif spec["state"] == "dikembalikan":
            odoo.create("pilar.approval.decision", {
                "po_id": po_id,
                "user_id": users.get(spec.get("checker", "sales")),
                "decision_type": "kembalikan",
                "reason": spec["return_note"],
                "decision_at": dt(submitted + timedelta(hours=1, minutes=30)),
            })
        elif spec["state"] == "dibatalkan":
            odoo.create("pilar.approval.decision", {
                "po_id": po_id,
                "user_id": users["sales"],
                "decision_type": "batal",
                "reason": spec["cancel_reason"],
                "decision_at": dt(submitted + timedelta(hours=2)),
            })

        auto_ids = odoo.search("pilar.audit.log", [
            ("po_id", "=", po_id),
            ("action_type", "=", "PO dibuat dari bukti Telegram"),
        ])
        if auto_ids:
            odoo.write("pilar.audit.log", auto_ids, {
                "created_at": dt(submitted),
                "new_status": "Bukti Diterima",
            })

        history = []
        if spec["state"] in ("dalam_pemeriksaan", "dikembalikan", "menunggu_keputusan",
                             "ditunda", "disahkan", "dibatalkan"):
            history.append(("Bukti pesanan diterima dari Telegram", False,
                            "Bukti Diterima", submitted))
        if spec["state"] in ("dikembalikan", "menunggu_keputusan", "ditunda", "disahkan"):
            history.append(("Pemeriksaan otomatis: lolos" if spec["state"] != "dikembalikan"
                            else "Pemeriksaan otomatis: bermasalah",
                            "Dalam Pemeriksaan", "Dalam Pemeriksaan",
                            submitted + timedelta(hours=1)))
        if spec["state"] in ("menunggu_keputusan", "ditunda", "disahkan"):
            history.append(("Diteruskan ke Director of Operational",
                            "Dalam Pemeriksaan", "Menunggu Keputusan",
                            submitted + timedelta(hours=2)))
        if spec["state"] == "disahkan":
            history.append(("PO disahkan", "Menunggu Keputusan", "Disahkan",
                            decision_time))
        if spec["state"] == "ditunda":
            history.append(("PO ditunda", "Menunggu Keputusan", "Ditunda",
                            decision_time))
        if spec["state"] == "dikembalikan":
            history.append(("PO dikembalikan untuk diperbaiki",
                            "Dalam Pemeriksaan", "Dikembalikan",
                            submitted + timedelta(hours=1, minutes=30)))
        if spec["state"] == "dibatalkan":
            history.append(("PO dibatalkan", "Bukti Diterima", "Dibatalkan",
                            submitted + timedelta(hours=2)))

        history.sort(key=lambda item: item[3])
        for position, (action, from_state, to_state, when) in enumerate(history):
            if position > 0:
                duration = (when - history[position - 1][3]).total_seconds() / 3600.0
            else:
                duration = 0.0
            odoo.create("pilar.audit.log", {
                "po_id": po_id,
                "version_id": version_id,
                "user_id": users["sales"],
                "action_type": action,
                "old_status": from_state or False,
                "new_status": to_state,
                "created_at": dt(when),
                "duration_hours": duration,
            })

        print(f"  {po['name']:<22} {STATUS_LABEL[po['state']]}")

    print(f"\nSelesai. {len(created)} PO demo dibuat.")
    print("Login role (password: pilar123):")
    for login in ("sales.pilar", "dirops.pilar", "exec.pilar", "finance.pilar",
                  "ops.pilar", "purchasing.pilar", "driver.pilar"):
        print(f"  - {login}")


if __name__ == "__main__":
    main()
