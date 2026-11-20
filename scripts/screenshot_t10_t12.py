#!/usr/bin/env python3
"""Screenshot alur "Catat Perubahan Pesanan" (T-10) dan "Batalkan PO Sah" (T-12).

Jalankan setelah scripts/seed_screens_t10_t12.py --out screenshots/seed_ids.json.
Semua aksi dilakukan lewat klik di UI Odoo (bukan RPC), sehingga label tombol,
status, dan dialog di gambar adalah tampilan asli Odoo.
"""

import argparse
import json
import os
import xmlrpc.client

from playwright.sync_api import sync_playwright

WIDTH, HEIGHT = 1440, 900


def xmlid_res_id(url, db, password, login, module, name):
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, login, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    rows = models.execute_kw(db, uid, password, "ir.model.data", "search_read",
                             [[("module", "=", module), ("name", "=", name)]],
                             {"fields": ["res_id"], "limit": 1})
    return rows[0]["res_id"]


class Capture:
    def __init__(self, browser, base_url, db, out):
        self.browser, self.base_url, self.db, self.out = browser, base_url, db, out
        self.saved, self.failed = [], []

    def login(self, login, password):
        context = self.browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT}, locale="id-ID",
        )
        page = context.new_page()
        page.goto(f"{self.base_url}/web/login?db={self.db}")
        page.fill("input[name=login]", login)
        page.fill("input[name=password]", password)
        page.click("button[type=submit]")
        page.wait_for_selector(".o_main_navbar", timeout=60000)
        return page

    def open_form(self, page, action_id, menu_id, record_id):
        page.goto(f"{self.base_url}/web#action={action_id}&menu_id={menu_id}"
                  f"&id={record_id}&model=pilar.po&view_type=form")
        self.wait_form(page)

    @staticmethod
    def wait_form(page):
        page.wait_for_selector(".o_form_view .o_statusbar_status", timeout=60000)
        page.wait_for_selector(".o_form_view .o_field_widget", timeout=60000)
        page.wait_for_function(
            "() => !document.querySelector('.o_loading_indicator, .o_blockUI')",
            timeout=30000,
        )
        page.wait_for_timeout(1200)

    @staticmethod
    def open_tab(page, label):
        page.locator(".o_notebook .nav-link", has_text=label).first.click()
        page.wait_for_timeout(600)

    def shot(self, page, name):
        """Full-page: perbesar tinggi viewport sampai seluruh isi form terlihat."""
        try:
            page.mouse.move(2, 2)
            extra = page.evaluate(
                "() => { const c = document.querySelector('.o_action_manager .o_content');"
                " if (!c) return 0; c.scrollTop = 0;"
                " return Math.max(c.scrollHeight - c.clientHeight, 0); }"
            )
            page.set_viewport_size({"width": WIDTH, "height": HEIGHT + extra})
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(self.out, name), full_page=True)
            page.set_viewport_size({"width": WIDTH, "height": HEIGHT})
            self.saved.append(name)
            print(f"  ok   {name}")
        except Exception as error:  # noqa: BLE001
            self.failed.append((name, str(error)))
            print(f"  GAGAL {name}: {error}")

    @staticmethod
    def expect_status(page, label):
        current = page.locator(".o_statusbar_status .o_arrow_button_current")
        current.filter(has_text=label).wait_for(timeout=30000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--db", default="odoo_app")
    parser.add_argument("--ids", default="screenshots/seed_ids.json")
    parser.add_argument("--out", default="screenshots")
    parser.add_argument("--password", default="pilar123")
    parser.add_argument("--admin", default="admin")
    parser.add_argument("--admin-password", default="admin")
    args = parser.parse_args()

    with open(args.ids, encoding="utf-8") as handle:
        ids = json.load(handle)
    os.makedirs(args.out, exist_ok=True)

    lookup = lambda name: xmlid_res_id(  # noqa: E731
        args.url, args.db, args.admin_password, args.admin, "pilar_po", name)
    approved_action = lookup("action_pilar_po_approved")
    root_menu = lookup("menu_pilar_po_root")
    change_id, cancel_id = ids["change"]["id"], ids["cancel"]["id"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        cap = Capture(browser, args.url, args.db, args.out)

        director = cap.login("dirops.pilar", args.password)
        sales = cap.login("sales.pilar", args.password)

        # 01: Director melihat PO Disahkan, tombol Batalkan PO Sah tampil.
        cap.open_form(director, approved_action, root_menu, change_id)
        director.locator("button[name=action_cancel]:visible",
                         has_text="Batalkan PO Sah").wait_for()
        cap.shot(director, "01_po_disahkan_sebagai_director.png")

        # 02: Sales mengisi Alasan Perubahan Pesanan, belum klik tombol.
        cap.open_form(sales, approved_action, root_menu, change_id)
        sales.locator("button[name=action_request_change]").wait_for()
        cap.open_tab(sales, "Pemeriksaan & Validasi")
        sales.locator("div[name=change_reason] textarea").fill(
            "Pelanggan menambah Beras Premium dari 120 kg menjadi 150 kg dan "
            "meminta pengiriman dimajukan pukul 06.00 (pesan Telegram Ibu Lestari)."
        )
        sales.wait_for_timeout(400)
        cap.shot(sales, "02_po_disahkan_sebagai_sales.png")

        # 03: Dialog konfirmasi perubahan.
        sales.locator("button[name=action_request_change]").click()
        sales.locator(".modal-dialog").wait_for()
        sales.wait_for_timeout(500)
        cap.shot(sales, "03_dialog_konfirmasi_perubahan.png")

        # 04: Setelah konfirmasi: Dalam Pemeriksaan, versi naik, tab Versi Dokumen.
        sales.locator(".modal-footer .btn-primary").click()
        cap.expect_status(sales, "Dalam Pemeriksaan")
        cap.wait_form(sales)
        cap.open_tab(sales, "Versi Dokumen")
        cap.shot(sales, "04_status_setelah_perubahan.png")

        # 05: Director mengisi alasan pembatalan pada PO Disahkan lain, klik tombol.
        cap.open_form(director, approved_action, root_menu, cancel_id)
        cap.open_tab(director, "Pemeriksaan & Validasi")
        director.locator("div[name=cancel_reason] textarea").fill(
            "Dapur SPPG MBG Cimahi libur operasional karena renovasi; "
            "pelanggan membatalkan pesanan lewat Telegram."
        )
        director.locator("button[name=action_cancel]:visible",
                         has_text="Batalkan PO Sah").click()
        director.locator(".modal-dialog").wait_for()
        director.wait_for_timeout(500)
        cap.shot(director, "05_dialog_konfirmasi_pembatalan.png")

        # 06: Setelah dibatalkan, tab Riwayat & Audit.
        director.locator(".modal-footer .btn-primary").click()
        cap.expect_status(director, "Dibatalkan")
        cap.wait_form(director)
        cap.open_tab(director, "Riwayat & Audit")
        cap.shot(director, "06_status_dibatalkan.png")

        browser.close()

    print(f"\nTersimpan: {len(cap.saved)}  Gagal: {len(cap.failed)}")
    for name, error in cap.failed:
        print(f"  {name}: {error}")


if __name__ == "__main__":
    main()
