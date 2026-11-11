#!/usr/bin/env python3
"""Bangun docs/tabel-screen-mockup.md dari docs/screen-mockup-data.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "docs/screen-mockup-data.json").read_text(encoding="utf-8"))
SCREENS = DATA["screens"]
USECASES = DATA["usecases"]
BY_LETTER = {screen["letter"]: screen for screen in SCREENS}


def screen_label(letter):
    screen = BY_LETTER[letter]
    return f"{letter}. Layar {screen['name']}"


def main():
    lines = [
        "# I.7 User Interface",
        "",
        "## I.7.1 Screen Mockup",
        "",
        "Spesifikasi layar pada sistem yang akan dibangun disusun berdasarkan implementasi "
        "pada **Odoo 17**. Sesuai ketentuan pada I.7.1, digunakan **Opsi 2: screenshot "
        "langsung hasil tampilan di Odoo 17**. Seluruh gambar diambil dari aplikasi yang "
        "berjalan pada `http://localhost:8069` dengan data demo; tidak ada tautan Figma "
        "karena tidak menggunakan Figma.",
        "",
        "> Versi Word siap tempel: "
        "[`Tabel-Screen-Mockup-Pilar.docx`](Tabel-Screen-Mockup-Pilar.docx).",
        "",
    ]

    for screen in SCREENS:
        lines.extend([
            f"### Tabel 1.7.{screen['no']} Tabel Screen Mockup Layar {screen['letter']} — {screen['name']}",
            "",
            f"| Nama Layar | Layar {screen['letter']} — {screen['name']} |",
            "|---|---|",
            f"| **Deskripsi Layar** | {screen['description']} |",
            f"| **User** | {screen['users']} |",
            f"| **Tampilan Layar** | ![Layar {screen['letter']} — {screen['name']}]"
            f"(screenshots/{screen['file']}) |",
            "",
        ])

    lines.extend([
        "## I.7.2 Pemetaan Layar",
        "",
        "Petakan use case sistem ke dalam layar/tampilan mockup yang telah dibuat.",
        "",
        "**Tabel 1.8 Tabel Pemetaan Layar**",
        "",
        "| No | Use Case / Activity | Layar |",
        "|----|---------------------|-------|",
    ])
    for usecase in USECASES:
        mapped = "<br>".join(screen_label(letter) for letter in usecase["screens"])
        lines.append(f"| {usecase['no']} | {usecase['name']} | {mapped} |")

    lines.extend([
        "",
        "## Lampiran — Cakupan Kebutuhan Fungsional",
        "",
        "| Kebutuhan | Layar Terkait |",
        "|-----------|---------------|",
        "| FR-01 Menerima PO & bukti dari Telegram | A, B |",
        "| FR-02 Mencatat isian PO terstruktur | B, C |",
        "| FR-03 Pemeriksaan kelengkapan otomatis | C, D |",
        "| FR-04 Meneruskan PO ke antrean keputusan | C, E |",
        "| FR-05 Pengembalian & perbaikan PO | B, D, G |",
        "| FR-06 Keputusan pengesahan PO | E, F |",
        "| FR-07 Riwayat status & audit | A, C, G, H, N |",
        "| FR-08 Aturan validasi & persetujuan | O |",
        "| FR-09 Pengingat batas waktu | A, E, I, O |",
        "| FR-10 Ringkasan PO tertunda (PDF) | I |",
        "| FR-11 PO sah untuk persiapan operasional | J |",
        "| FR-12 Kebutuhan barang untuk Purchasing | K |",
        "| FR-13 PO sah sebagai dasar tagihan | L |",
        "| FR-14 Informasi pesanan untuk Head of Driver | M |",
        "| FR-15 Pencatatan pembatalan PO | F, H, N |",
        "",
        "## Catatan Reproduksi Mockup",
        "",
        "1. Jalankan `./scripts/init.sh` untuk menyalakan PostgreSQL dan Odoo 17.",
        "2. Jalankan `python3 scripts/seed_demo.py` untuk membuat pengguna per peran dan "
        "23 PO contoh pada seluruh status.",
        "3. Jalankan `python3 scripts/screenshot.py` untuk mengambil ulang seluruh mockup ke "
        "`docs/screenshots/`.",
        "4. Login aplikasi: `http://localhost:8069`, pengguna `admin`, kata sandi `admin`. "
        "Pengguna per peran menggunakan kata sandi `pilar123`.",
        "",
    ])

    (ROOT / "docs/tabel-screen-mockup.md").write_text("\n".join(lines), encoding="utf-8")
    print("docs/tabel-screen-mockup.md dibuat")


if __name__ == "__main__":
    main()
